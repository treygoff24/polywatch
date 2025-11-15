from pathlib import Path
from typing import Dict, List
from unittest import TestCase

from fastapi.testclient import TestClient

from polywatch.reporting import ReportEnvelope
from polywatch.service import ServiceConfig, create_app


class FakeBuilder:
    def __init__(self) -> None:
        self.calls: List[Dict[str, object]] = []

    def build(self, slug: str, lookback_seconds: int, **kwargs) -> ReportEnvelope:
        self.calls.append({"slug": slug, "lookback": lookback_seconds, **kwargs})
        payload = {"event": {"title": slug.title(), "slug": slug, "id": 1}, "analytics": {}}
        summary = {
            "slug": slug,
            "eventId": 1,
            "title": slug.title(),
            "label": "normal",
            "score": 0.0,
            "updatedAt": "2024-01-01T00:00:00Z",
            "lookbackSeconds": lookback_seconds,
            "tradeCount": 0,
            "lastTradeTimestamp": None,
            "topSignals": [],
            "outcomes": [],
        }
        return ReportEnvelope(
            slug=slug,
            payload=payload,
            summary=summary,
            trade_count=0,
            lookback_seconds=lookback_seconds,
        )


class FakeStore:
    def __init__(self) -> None:
        self.reports: Dict[str, Dict[str, object]] = {}
        self.summaries: List[Dict[str, object]] = []

    def write_report(self, slug: str, payload: Dict[str, object]) -> None:
        self.reports[slug] = payload

    def read_report(self, slug: str):
        return self.reports.get(slug)

    def upsert_summary(self, summary: Dict[str, object], *, refresh_mode: str) -> None:
        entry = dict(summary)
        entry["refreshMode"] = refresh_mode
        self.summaries = [item for item in self.summaries if item.get("slug") != summary["slug"]]
        self.summaries.append(entry)

    def list_reports(self) -> List[Dict[str, object]]:
        return list(self.summaries)


class FakeSearchClient:
    def __init__(self, events: List[Dict[str, object]]):
        self.events = events

    def search(self, query: str, *, limit: int) -> List[Dict[str, object]]:
        return self.events


def _config() -> ServiceConfig:
    return ServiceConfig(
        reports_root=Path("unused"),
        index_path=Path("unused/index.json"),
        default_slugs={"honduras-presidential-election"},
        on_demand_lookback=3600,
        page_limit=5000,
        max_pages=50,
        sleep_seconds=0.3,
        search_limit=10,
    )


class ServiceTest(TestCase):
    def test_refresh_endpoint_builds_and_persists(self) -> None:
        builder = FakeBuilder()
        store = FakeStore()
        app = create_app(
            config=_config(),
            builder=builder,
            store=store,
            search_client=FakeSearchClient([]),
        )
        client = TestClient(app)

        response = client.post("/reports/custom-market/refresh", json={"lookback": "2h"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ready")
        self.assertIn("report", data)
        self.assertIn("custom-market", store.reports)
        self.assertEqual(builder.calls[0]["lookback"], 7200)

    def test_get_report_404_when_missing(self) -> None:
        app = create_app(
            config=_config(),
            builder=FakeBuilder(),
            store=FakeStore(),
            search_client=FakeSearchClient([]),
        )
        client = TestClient(app)
        response = client.get("/reports/unknown-market")
        self.assertEqual(response.status_code, 404)

    def test_search_returns_cached_summary(self) -> None:
        store = FakeStore()
        cached = {
            "slug": "known-market",
            "eventId": 1,
            "title": "Known",
            "label": "normal",
            "score": 1.0,
            "updatedAt": "2024-01-01T00:00:00Z",
            "lookbackSeconds": 3600,
            "tradeCount": 0,
            "lastTradeTimestamp": None,
            "topSignals": [],
            "outcomes": [],
            "refreshMode": "on-demand",
        }
        store.summaries.append(cached)
        search_events = [{"slug": "known-market", "title": "Known Market", "id": 1, "status": "open"}]
        app = create_app(
            config=_config(),
            builder=FakeBuilder(),
            store=store,
            search_client=FakeSearchClient(search_events),
        )
        client = TestClient(app)
        response = client.get("/search?q=known")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertIsNotNone(results[0]["cachedReport"])
