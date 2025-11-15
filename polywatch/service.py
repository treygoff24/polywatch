from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List, Optional, Sequence, Set

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .api import GAMMA_BASE, PolymarketClient
from .reporting import ReportBuilder, ReportEnvelope, ReportStore
from .utils import parse_lookback

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceConfig:
    reports_root: Path
    index_path: Path
    default_slugs: Set[str]
    on_demand_lookback: int
    page_limit: int
    max_pages: int
    sleep_seconds: float
    search_limit: int


def _env_set(name: str, fallback: str) -> Set[str]:
    raw = os.environ.get(name, fallback)
    return {item.strip() for item in raw.split(",") if item.strip()}


def load_service_config() -> ServiceConfig:
    reports_root = Path(os.environ.get("REPORTS_FILE_ROOT", "docs/reports"))
    index_path = Path(os.environ.get("REPORTS_INDEX_FILE", reports_root / "index.json"))
    default_slugs = _env_set(
        "POLYWATCH_DEFAULT_SLUGS",
        "honduras-presidential-election",
    )
    lookback_default = os.environ.get("POLYWATCH_ON_DEMAND_LOOKBACK", "24h")
    on_demand_lookback = parse_lookback(lookback_default)
    page_limit = int(os.environ.get("POLYWATCH_PAGE_LIMIT", "5000"))
    max_pages = int(os.environ.get("POLYWATCH_MAX_PAGES", "50"))
    sleep_seconds = float(os.environ.get("POLYWATCH_SLEEP_SECONDS", "0.3"))
    search_limit = int(os.environ.get("POLYWATCH_SEARCH_LIMIT", "10"))
    return ServiceConfig(
        reports_root=reports_root,
        index_path=index_path,
        default_slugs=default_slugs,
        on_demand_lookback=on_demand_lookback,
        page_limit=page_limit,
        max_pages=max_pages,
        sleep_seconds=sleep_seconds,
        search_limit=max(1, search_limit),
    )


class MarketSearchClient:
    def __init__(self, base_url: str = GAMMA_BASE, session: Optional[requests.Session] = None):
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def search(self, query: str, *, limit: int) -> List[Dict[str, object]]:
        params = {
            "limit": limit,
            "status": "open",
        }
        if query:
            params["search"] = query
        url = f"{self.base_url}/events"
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            if isinstance(payload.get("events"), list):
                return payload["events"]
            if isinstance(payload.get("data"), list):
                return payload["data"]
        if isinstance(payload, list):
            return payload
        raise RuntimeError("Unexpected search payload shape")


class RefreshRequest(BaseModel):
    lookback: Optional[str] = None
    page_limit: Optional[int] = None
    max_pages: Optional[int] = None


class BuildCoordinator:
    def __init__(self) -> None:
        self._locks: Dict[str, Lock] = {}

    def run(self, slug: str, builder: Callable[[], ReportEnvelope]) -> ReportEnvelope:
        lock = self._locks.setdefault(slug, Lock())
        with lock:
            return builder()


def create_app(
    *,
    config: Optional[ServiceConfig] = None,
    builder: Optional[ReportBuilder] = None,
    store: Optional[ReportStore] = None,
    search_client: Optional[MarketSearchClient] = None,
) -> FastAPI:
    config = config or load_service_config()
    builder = builder or ReportBuilder(PolymarketClient())
    store = store or ReportStore(config.reports_root, index_path=config.index_path)
    search_client = search_client or MarketSearchClient()
    coordinator = BuildCoordinator()

    app = FastAPI(title="Polywatch Service")

    def refresh_mode(slug: str) -> str:
        return "scheduled" if slug in config.default_slugs else "on-demand"

    def cached_index() -> Dict[str, Dict[str, object]]:
        return {entry["slug"]: entry for entry in store.list_reports()}

    @app.get("/healthz")
    def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    @app.get("/reports/index")
    def report_index() -> Dict[str, object]:
        return store.read_index()

    @app.get("/reports/{slug}")
    def get_report(slug: str):
        payload = store.read_report(slug)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Report {slug} not found")
        return JSONResponse(payload)

    @app.post("/reports/{slug}/refresh")
    def refresh_report(slug: str, request: RefreshRequest = RefreshRequest()):
        try:
            lookback_seconds = (
                parse_lookback(request.lookback) if request.lookback else config.on_demand_lookback
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        page_limit = request.page_limit or config.page_limit
        max_pages = request.max_pages or config.max_pages

        def _build() -> ReportEnvelope:
            return builder.build(
                slug,
                lookback_seconds=lookback_seconds,
                page_limit=page_limit,
                max_pages=max_pages,
                sleep_seconds=config.sleep_seconds,
            )

        try:
            envelope = coordinator.run(slug, _build)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to refresh %s", slug)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        store.write_report(slug, envelope.payload)
        store.upsert_summary(envelope.summary, refresh_mode=refresh_mode(slug))
        return {
            "status": "ready",
            "report": envelope.payload,
            "summary": envelope.summary,
        }

    @app.get("/search")
    def search_markets(
        q: str = Query("", max_length=120),
        limit: int = Query(10, ge=1, le=50),
    ) -> Dict[str, object]:
        effective_limit = min(limit, config.search_limit)
        try:
            markets = search_client.search(q, limit=effective_limit)
        except requests.RequestException as exc:
            logger.error("Search request failed: %s", exc)
            raise HTTPException(status_code=502, detail="Upstream search failed") from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("Search payload error: %s", exc)
            raise HTTPException(status_code=500, detail="Unable to process search response") from exc

        summaries = cached_index()
        results: List[Dict[str, object]] = []
        for market in markets:
            slug = market.get("slug") or market.get("urlSlug") or market.get("event_slug")
            if not slug:
                continue
            title = market.get("title") or market.get("question") or slug
            event_id = market.get("id") or market.get("eventId")
            try:
                event_id = int(event_id)
            except (TypeError, ValueError):
                event_id = None
            result = {
                "slug": slug,
                "title": title,
                "eventId": event_id,
                "status": market.get("status"),
                "cachedReport": summaries.get(slug),
            }
            results.append(result)
        return {"results": results}

    return app


app = create_app()

__all__ = ["create_app", "app", "ServiceConfig", "load_service_config", "MarketSearchClient"]
