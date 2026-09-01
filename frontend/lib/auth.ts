// Token storage for the SPA. Tokens live in localStorage rather than an
// httpOnly cookie because the backend issues them as a JSON body, not a
// Set-Cookie header (see docs/api-design.md § Auth flow) — a deliberate
// Phase 5 API contract this client has to consume as-is. Known tradeoff:
// localStorage is readable by any script on the page (XSS risk), whereas an
// httpOnly refresh-token cookie would not be. Revisiting this to a
// cookie-based flow is a reasonable Phase 13 hardening step, not done here
// since it would mean changing the already-verified Phase 5 backend
// contract along with it.

const ACCESS_TOKEN_KEY = "dra.access_token";
const REFRESH_TOKEN_KEY = "dra.refresh_token";

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  return isBrowser() ? localStorage.getItem(ACCESS_TOKEN_KEY) : null;
}

export function getRefreshToken(): string | null {
  return isBrowser() ? localStorage.getItem(REFRESH_TOKEN_KEY) : null;
}

export function setTokens(accessToken: string, refreshToken: string): void {
  if (!isBrowser()) return;
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearTokens(): void {
  if (!isBrowser()) return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function hasAccessToken(): boolean {
  return getAccessToken() !== null;
}
