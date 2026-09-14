import { ViolationSeverity, ViolationType } from "./api";

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

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  });
}
