import { TokenPair } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `Ошибка запроса (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // тело не JSON — оставляем дефолтное сообщение
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export function requestRegisterCode(phone: string): Promise<void> {
  return postJson("/api/auth/register/request-code", { phone });
}

export function confirmRegister(
  phone: string,
  code: string,
  organizationName: string,
  userName: string
): Promise<TokenPair> {
  return postJson("/api/auth/register/confirm", {
    phone,
    code,
    organization_name: organizationName,
    user_name: userName,
  });
}

export function requestLoginCode(phone: string): Promise<void> {
  return postJson("/api/auth/login/request-code", { phone });
}

export function confirmLogin(phone: string, code: string): Promise<TokenPair> {
  return postJson("/api/auth/login/confirm", { phone, code });
}

export function refreshTokens(refreshToken: string): Promise<TokenPair> {
  return postJson("/api/auth/refresh", { refresh_token: refreshToken });
}
