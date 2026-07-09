// Armazenamento dos tokens JWT.
//
// MVP: localStorage por simplicidade. Ciente do trade-off de XSS — quando o
// backend expuser refresh via cookie httpOnly, migrar para lá. Access token é
// curto (~15 min) e o refresh é rotativo/revogável no servidor.

const ACCESS_KEY = "ge.access_token";
const REFRESH_KEY = "ge.refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}
