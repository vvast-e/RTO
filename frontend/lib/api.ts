import { authFetch, TokenPair } from "./auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Ошибка API с HTTP-статусом — позволяет отличать 402 (лимит/истёкшая
 * подписка) от прочих ошибок и показывать пользователю целевое действие
 * (например, ссылку на /subscription), а не только текст detail. */
export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseJsonResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Ошибка запроса (${res.status})`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // тело не JSON — оставляем дефолтное сообщение
    }
    throw new ApiError(res.status, detail);
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

/** Авторизованный PATCH через authFetch (подставляет/обновляет access-токен). */
async function authPatchJson<T>(path: string, body: unknown): Promise<T> {
  const res = await authFetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
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
  license_expiry_date: string | null;
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
  license_expiry_date?: string;
}

export function createDriver(payload: DriverCreatePayload): Promise<Driver> {
  return authPostJson("/api/drivers", payload);
}

export interface DriverUpdatePayload {
  full_name?: string;
  phone?: string;
  license_number?: string;
  tachograph_card_number?: string;
  license_expiry_date?: string | null;
}

export function updateDriver(id: string, payload: DriverUpdatePayload): Promise<Driver> {
  return authPatchJson(`/api/drivers/${id}`, payload);
}

export type VehicleStatus = "active" | "repair" | "inactive";

export interface Vehicle {
  id: string;
  plate_number: string;
  brand_model: string;
  tachograph_type: string | null;
  status: VehicleStatus;
  next_inspection_date: string | null;
}

export interface VehicleCreatePayload {
  plate_number: string;
  brand_model: string;
  tachograph_type?: string;
  status?: VehicleStatus;
  next_inspection_date?: string;
}

export function listVehicles(): Promise<Vehicle[]> {
  return authGetJson("/api/vehicles");
}

export function createVehicle(payload: VehicleCreatePayload): Promise<Vehicle> {
  return authPostJson("/api/vehicles", payload);
}

export interface VehicleUpdatePayload {
  plate_number?: string;
  brand_model?: string;
  tachograph_type?: string;
  status?: VehicleStatus;
  next_inspection_date?: string | null;
}

export function updateVehicle(id: string, payload: VehicleUpdatePayload): Promise<Vehicle> {
  return authPatchJson(`/api/vehicles/${id}`, payload);
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

export type ReminderType =
  | "rto_deadline"
  | "etrn_deadline"
  | "vehicle_inspection"
  | "driver_license_expiry"
  | "custom";

export interface Reminder {
  id: string;
  organization_id: string;
  type: ReminderType;
  target_date: string;
  sent: boolean;
  telegram_message_id: number | null;
  created_at: string;
}

export interface ReminderCreatePayload {
  type: ReminderType;
  target_date: string;
}

export interface ReminderFilters {
  sent?: boolean;
  type?: ReminderType;
}

export function listReminders(filters: ReminderFilters = {}): Promise<Reminder[]> {
  const params = new URLSearchParams();
  if (filters.sent !== undefined) params.set("sent", String(filters.sent));
  if (filters.type) params.set("type", filters.type);
  const query = params.toString();
  return authGetJson(`/api/reminders${query ? `?${query}` : ""}`);
}

export function createReminder(payload: ReminderCreatePayload): Promise<Reminder> {
  return authPostJson("/api/reminders", payload);
}

export function sendReminder(id: string): Promise<Reminder> {
  return authPostJson(`/api/reminders/${id}/send`);
}

export interface OrganizationMe {
  name: string;
  telegram_linked: boolean;
}

export function getOrganizationMe(): Promise<OrganizationMe> {
  return authGetJson("/api/organizations/me");
}

export interface TelegramLinkCode {
  code: string;
  expires_at: string;
}

export function getTelegramLinkCode(): Promise<TelegramLinkCode> {
  return authPostJson("/api/organizations/me/telegram-link-code");
}

export type SubscriptionPlan = "starter" | "pro" | "fleet";
export type SubscriptionStatus = "active" | "trial" | "expired";

export interface Subscription {
  id: string;
  plan: SubscriptionPlan;
  status: SubscriptionStatus;
  vehicles_limit: number;
  vehicles_used: number;
  price: number;
  next_billing_date: string | null;
}

export interface SubscriptionUpdatePayload {
  plan?: SubscriptionPlan;
  status?: SubscriptionStatus;
  vehicles_limit?: number;
  price?: number;
  next_billing_date?: string | null;
}

export function getSubscription(): Promise<Subscription> {
  return authGetJson("/api/subscriptions/me");
}

export function updateSubscription(payload: SubscriptionUpdatePayload): Promise<Subscription> {
  return authPatchJson("/api/subscriptions/me", payload);
}

export type TripStatus = "planned" | "in_progress" | "completed";

export interface Trip {
  id: string;
  vehicle_id: string;
  driver_id: string;
  start_datetime: string;
  end_datetime: string | null;
  start_location: string | null;
  end_location: string | null;
  distance_km: number | null;
  status: TripStatus;
}

export interface TripCreatePayload {
  vehicle_id: string;
  driver_id: string;
  start_datetime: string;
  end_datetime?: string;
  start_location?: string;
  end_location?: string;
  distance_km?: number;
  status?: TripStatus;
}

export function listTrips(): Promise<Trip[]> {
  return authGetJson("/api/trips");
}

export function createTrip(payload: TripCreatePayload): Promise<Trip> {
  return authPostJson("/api/trips", payload);
}

export type WaybillStatus = "draft" | "issued";

export interface Waybill {
  id: string;
  trip_id: string;
  document_number: string;
  issue_date: string;
  pdf_file_url: string | null;
  status: WaybillStatus;
  created_at: string;
}

export interface WaybillCreatePayload {
  trip_id: string;
  document_number: string;
  issue_date: string;
}

export function listWaybills(tripId?: string): Promise<Waybill[]> {
  const query = tripId ? `?trip_id=${tripId}` : "";
  return authGetJson(`/api/waybills${query}`);
}

export function createWaybill(payload: WaybillCreatePayload): Promise<Waybill> {
  return authPostJson("/api/waybills", payload);
}

export function issueWaybill(id: string): Promise<Waybill> {
  return authPostJson(`/api/waybills/${id}/issue`);
}

export function generateWaybill(id: string): Promise<Waybill> {
  return authPostJson(`/api/waybills/${id}/generate`);
}

/** Скачивание PDF требует Authorization-заголовок, обычная <a href> ссылка
 * его не приложит — качаем через authFetch как blob и открываем локальную
 * ссылку на него. */
export async function downloadWaybillPdf(id: string, filename: string): Promise<void> {
  const res = await authFetch(`/api/waybills/${id}/pdf`);
  if (!res.ok) {
    throw new ApiError(res.status, "Не удалось скачать PDF");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
