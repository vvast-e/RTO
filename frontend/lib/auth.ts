/**
 * Хранение JWT на клиенте.
 *
 * Выбор: localStorage, а не httpOnly cookie. Для MVP фронтенд — чистый
 * client-side SPA без серверного рендеринга приватных страниц, поэтому
 * httpOnly cookie не даёт защиты, которая была бы недоступна и так (нет SSR,
 * который читал бы её на сервере), а localStorage сильно проще в связке с
 * fetch на клиенте. Компромисс — токены уязвимы к XSS; если это станет
 * важным, стоит перейти на httpOnly cookie + BFF-прокси перед продом.
 */

const ACCESS_TOKEN_KEY = "rto_access_token";
const REFRESH_TOKEN_KEY = "rto_refresh_token";

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(tokens: TokenPair): void {
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}
