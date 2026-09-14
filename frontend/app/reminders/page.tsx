"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  Reminder,
  ReminderType,
  createReminder,
  listReminders,
  sendReminder,
} from "@/lib/api";
import { REMINDER_TYPE_LABELS } from "@/lib/labels";

const REMINDER_TYPES: ReminderType[] = [
  "rto_deadline",
  "etrn_deadline",
  "vehicle_inspection",
  "custom",
];

export default function RemindersPage() {
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sendingId, setSendingId] = useState<string | null>(null);

  const [type, setType] = useState<ReminderType>("rto_deadline");
  const [targetDate, setTargetDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function load() {
    setLoading(true);
    setError(null);
    listReminders()
      .then(setReminders)
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить напоминания"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!targetDate) {
      setFormError("Укажите дату напоминания");
      return;
    }
    setSubmitting(true);
    try {
      const reminder = await createReminder({ type, target_date: targetDate });
      setReminders((prev) => [...prev, reminder]);
      setTargetDate("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Не удалось добавить напоминание");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSend(id: string) {
    setSendingId(id);
    try {
      const updated = await sendReminder(id);
      setReminders((prev) => prev.map((r) => (r.id === id ? updated : r)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить напоминание");
    } finally {
      setSendingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Напоминания</h1>

      <form
        onSubmit={handleSubmit}
        className="mt-4 flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <div>
          <label className="block text-sm font-medium">Тип</label>
          <select
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={type}
            onChange={(e) => setType(e.target.value as ReminderType)}
          >
            {REMINDER_TYPES.map((t) => (
              <option key={t} value={t}>
                {REMINDER_TYPE_LABELS[t]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Дата*</label>
          <input
            type="date"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={targetDate}
            onChange={(e) => setTargetDate(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {submitting ? "Добавление..." : "Добавить"}
        </button>
        {formError && <p className="w-full text-sm text-red-600">{formError}</p>}
      </form>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && reminders.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">Напоминаний пока нет.</p>
      )}

      {!loading && !error && reminders.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 pr-4">Тип</th>
                <th className="py-2 pr-4">Дата</th>
                <th className="py-2 pr-4">Статус</th>
                <th className="py-2 pr-4" />
              </tr>
            </thead>
            <tbody>
              {reminders.map((r) => (
                <tr key={r.id} className="border-b">
                  <td className="py-2 pr-4">{REMINDER_TYPE_LABELS[r.type]}</td>
                  <td className="py-2 pr-4">{r.target_date}</td>
                  <td className="py-2 pr-4">{r.sent ? "Отправлено" : "Не отправлено"}</td>
                  <td className="py-2 pr-4">
                    {!r.sent && (
                      <button
                        type="button"
                        disabled={sendingId === r.id}
                        onClick={() => handleSend(r.id)}
                        className="text-sm text-gray-900 underline disabled:opacity-50"
                      >
                        {sendingId === r.id ? "..." : "Отправить"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
