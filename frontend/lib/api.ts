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

export interface DriverCreatePayload {
  full_name: string;
  phone?: string;
  license_number?: string;
  tachograph_card_number?: string;
}

export function createDriver(payload: DriverCreatePayload): Promise<Driver> {
  return authPostJson("/api/drivers", payload);
}

export type VehicleStatus = "active" | "repair" | "inactive";

export interface Vehicle {
  id: string;
  plate_number: string;
  brand_model: string;
  tachograph_type: string | null;
  status: VehicleStatus;
}

export interface VehicleCreatePayload {
  plate_number: string;
  brand_model: string;
  tachograph_type?: string;
  status?: VehicleStatus;
}

export function listVehicles(): Promise<Vehicle[]> {
  return authGetJson("/api/vehicles");
}

export function createVehicle(payload: VehicleCreatePayload): Promise<Vehicle> {
  return authPostJson("/api/vehicles", payload);
}

export type EntryType = "driving" | "rest" | "other_work" | "availability";

export interface WorkTimeEntry {
  id: string;
  driver_id: string;
  trip_id: string | null;
  entry_type: EntryType;
  start_time: string;
  end_time: string | null;
  source: "manual" | "import";
}

export interface WorkTimeEntryCreatePayload {
  driver_id: string;
  entry_type: EntryType;
  start_time: string;
  end_time?: string;
}

export function createWorktimeEntry(payload: WorkTimeEntryCreatePayload): Promise<WorkTimeEntry> {
  return authPostJson("/api/worktime", payload);
}

export interface WorktimeImportRowError {
  row_number: number;
  reason: string;
}

export interface WorktimeImportReport {
  created: number;
  skipped_duplicates: number;
  failed: number;
  errors: WorktimeImportRowError[];
  created_entry_ids: string[];
}

export async function importWorktimeFile(file: File): Promise<WorktimeImportReport> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await authFetch("/api/worktime/import", {
    method: "POST",
    body: formData,
  });
  return parseJsonResponse<WorktimeImportReport>(res);
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
