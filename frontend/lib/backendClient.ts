const BACKEND_BASE_URL = process.env.POLYWATCH_BACKEND_URL;

function ensureBackendUrl(): string {
  if (!BACKEND_BASE_URL) {
    throw new Error(
      "POLYWATCH_BACKEND_URL is not configured. Set it to the FastAPI service origin."
    );
  }
  return BACKEND_BASE_URL;
}

function buildBackendUrl(path: string): string {
  const base = ensureBackendUrl().replace(/\/+$/, "");
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalizedPath}`;
}

export async function backendFetch(
  path: string,
  init?: RequestInit
): Promise<Response> {
  const url = buildBackendUrl(path);
  const headers = {
    Accept: "application/json",
    ...(init?.headers ?? {})
  };
  return fetch(url, {
    ...init,
    headers,
    cache: "no-store"
  });
}

export function isBackendConfigured(): boolean {
  return Boolean(BACKEND_BASE_URL);
}
