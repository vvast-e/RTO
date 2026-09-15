import {
  EntryType,
  ReminderType,
  SubscriptionPlan,
  SubscriptionStatus,
  TripStatus,
  VehicleStatus,
  ViolationSeverity,
  ViolationType,
  WaybillStatus,
} from "./api";

export const VIOLATION_TYPE_LABELS: Record<ViolationType, string> = {
  daily_driving_exceeded: "Превышение суточного вождения",
  continuous_driving_exceeded: "Превышение непрерывного вождения",
  daily_rest_insufficient: "Недостаточный суточный отдых",
  weekly_rest_insufficient: "Недостаточный еженедельный отдых",
  biweekly_driving_exceeded: "Превышение вождения за 2 недели",
};

export const VIOLATION_SEVERITY_LABELS: Record<ViolationSeverity, string> = {
  warning: "Предупреждение",
  violation: "Нарушение",
};

export const ENTRY_TYPE_LABELS: Record<EntryType, string> = {
  driving: "Вождение",
  rest: "Отдых",
  other_work: "Другая работа",
  availability: "Присутствие",
};

export const VEHICLE_STATUS_LABELS: Record<VehicleStatus, string> = {
  active: "На линии",
  repair: "В ремонте",
  inactive: "Не используется",
};

export const REMINDER_TYPE_LABELS: Record<ReminderType, string> = {
  rto_deadline: "Срок РТО",
  etrn_deadline: "Срок ЭТрН",
  vehicle_inspection: "Техосмотр",
  driver_license_expiry: "Истечение прав",
  custom: "Другое",
};

export const SUBSCRIPTION_PLAN_LABELS: Record<SubscriptionPlan, string> = {
  starter: "Starter",
  pro: "Pro",
  fleet: "Fleet",
};

export const SUBSCRIPTION_STATUS_LABELS: Record<SubscriptionStatus, string> = {
  active: "Активна",
  trial: "Пробный период",
  expired: "Истекла",
};

export const TRIP_STATUS_LABELS: Record<TripStatus, string> = {
  planned: "Запланирован",
  in_progress: "В пути",
  completed: "Завершён",
};

export const WAYBILL_STATUS_LABELS: Record<WaybillStatus, string> = {
  draft: "Черновик",
  issued: "Выдан",
};

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}
