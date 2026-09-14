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

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

let refreshPromise: Promise<TokenPair> | null = null;

/**
 * Обновляет access-токен через refresh-токен. Параллельные вызовы (несколько
 * запросов, упавших с 401 одновременно) шарят один промис, чтобы не слать
 * несколько /api/auth/refresh подряд.
 */
async function doRefresh(): Promise<TokenPair> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error("Не удалось обновить сессию");

  if (!refreshPromise) {
    refreshPromise = fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Не удалось обновить сессию");
        return res.json() as Promise<TokenPair>;
      })
      .then((tokens) => {
        setTokens(tokens);
        return tokens;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/**
 * fetch с авторизацией: подставляет access-токен, а при 401 один раз
 * пробует обновить его через refresh-токен и повторяет запрос. Если
 * обновить не удалось — чистит токены и редиректит на /login.
 */
export async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const withAuth = (token: string | null): RequestInit => ({
    ...init,
    headers: {
      ...(init.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });

  let res = await fetch(`${API_URL}${path}`, withAuth(getAccessToken()));

  if (res.status === 401) {
    try {
      const tokens = await doRefresh();
      res = await fetch(`${API_URL}${path}`, withAuth(tokens.access_token));
    } catch {
      clearTokens();
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new Error("Сессия истекла, войдите снова");
    }
  }

  return res;
}
