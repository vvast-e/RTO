import { authFetch, TokenPair } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function parseJsonResponse<T>(res: Response): Promise<T> {
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

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJsonResponse<T>(res);
}

/** Авторизованный GET через authFetch (подставляет/обновляет access-токен). */
async function authGetJson<T>(path: string): Promise<T> {
  const res = await authFetch(path, { method: "GET" });
  return parseJsonResponse<T>(res);
}

/** Авторизованный POST через authFetch (подставляет/обновляет access-токен). */
async function authPostJson<T>(path: string, body?: unknown): Promise<T> {
  const res = await authFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return parseJsonResponse<T>(res);
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

export interface Driver {
  id: string;
  full_name: string;
  phone: string | null;
  license_number: string | null;
  tachograph_card_number: string | null;
  created_at: string;
}

export function listDrivers(): Promise<Driver[]> {
  return authGetJson("/api/drivers");
}

export type ViolationType =
  | "daily_driving_exceeded"
  | "continuous_driving_exceeded"
  | "daily_rest_insufficient"
  | "weekly_rest_insufficient"
  | "biweekly_driving_exceeded";

export type ViolationSeverity = "warning" | "violation";

export interface Violation {
  id: string;
  driver_id: string;
  trip_id: string | null;
  violation_type: ViolationType;
  severity: ViolationSeverity;
  detected_at: string;
  description: string | null;
  resolved: boolean;
}

export interface ViolationFilters {
  driver_id?: string;
  date_from?: string;
  date_to?: string;
  severity?: ViolationSeverity;
  resolved?: boolean;
}

export function listViolations(filters: ViolationFilters = {}): Promise<Violation[]> {
  const params = new URLSearchParams();
  if (filters.driver_id) params.set("driver_id", filters.driver_id);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.severity) params.set("severity", filters.severity);
  if (filters.resolved !== undefined) params.set("resolved", String(filters.resolved));
  const query = params.toString();
  return authGetJson(`/api/violations${query ? `?${query}` : ""}`);
}

export function resolveViolation(id: string): Promise<Violation> {
  return authPostJson(`/api/violations/${id}/resolve`);
}
