"use client";

import { FormEvent, useEffect, useRef, useState } from "react";

import {
  createWorktimeEntry,
  Driver,
  EntryType,
  importWorktimeFile,
  listDrivers,
  WorktimeImportReport,
} from "@/lib/api";
import { ENTRY_TYPE_LABELS } from "@/lib/labels";

export default function WorktimePage() {
  const [drivers, setDrivers] = useState<Driver[]>([]);

  const [driverId, setDriverId] = useState("");
  const [entryType, setEntryType] = useState<EntryType>("driving");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importReport, setImportReport] = useState<WorktimeImportReport | null>(null);

  useEffect(() => {
    listDrivers().then(setDrivers).catch(() => {});
  }, []);

  async function handleManualSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    if (!driverId) {
      setFormError("Выберите водителя");
      return;
    }
    if (!startTime) {
      setFormError("Укажите время начала");
      return;
    }

    setSubmitting(true);
    try {
      await createWorktimeEntry({
        driver_id: driverId,
        entry_type: entryType,
        start_time: new Date(startTime).toISOString(),
        end_time: endTime ? new Date(endTime).toISOString() : undefined,
      });
      setFormSuccess("Запись добавлена");
      setStartTime("");
      setEndTime("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Не удалось добавить запись");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleImport(e: FormEvent) {
    e.preventDefault();
    setImportError(null);
    setImportReport(null);

    const file = fileInputRef.current?.files?.[0];
    if (!file) {
      setImportError("Выберите файл выгрузки тахографа");
      return;
    }

    setImporting(true);
    try {
      const report = await importWorktimeFile(file);
      setImportReport(report);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setImportError(err instanceof Error ? err.message : "Не удалось импортировать файл");
    } finally {
      setImporting(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Рабочее время</h1>

      <section className="mt-4 rounded border p-4">
        <h2 className="text-lg font-medium">Ручной ввод записи</h2>
        <form onSubmit={handleManualSubmit} className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-sm font-medium">Водитель*</label>
            <select
              className="mt-1 rounded border px-3 py-2 text-sm"
              value={driverId}
              onChange={(e) => setDriverId(e.target.value)}
            >
              <option value="">Выберите водителя</option>
              {drivers.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium">Тип записи</label>
            <select
              className="mt-1 rounded border px-3 py-2 text-sm"
              value={entryType}
              onChange={(e) => setEntryType(e.target.value as EntryType)}
            >
              {Object.entries(ENTRY_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium">Начало*</label>
            <input
              type="datetime-local"
              className="mt-1 rounded border px-3 py-2 text-sm"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium">Окончание</label>
            <input
              type="datetime-local"
              className="mt-1 rounded border px-3 py-2 text-sm"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
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
          {formSuccess && <p className="w-full text-sm text-green-700">{formSuccess}</p>}
        </form>
      </section>

      <section className="mt-4 rounded border p-4">
        <h2 className="text-lg font-medium">Импорт из тахографа</h2>
        <form onSubmit={handleImport} className="mt-3 flex flex-wrap items-end gap-3">
          <div>
            <label className="block text-sm font-medium">Файл (.csv, .xlsx)</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              className="mt-1 block text-sm"
            />
          </div>
          <button
            type="submit"
            disabled={importing}
            className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          >
            {importing ? "Импорт..." : "Импортировать"}
          </button>
        </form>
        {importError && <p className="mt-2 text-sm text-red-600">{importError}</p>}

        {importReport && (
          <div className="mt-4 text-sm">
            <p>
              Создано: <span className="font-medium">{importReport.created}</span>, пропущено
              дублей: <span className="font-medium">{importReport.skipped_duplicates}</span>,
              ошибок: <span className="font-medium">{importReport.failed}</span>
            </p>
            {importReport.errors.length > 0 && (
              <div className="mt-2 overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b text-left text-gray-500">
                      <th className="py-2 pr-4">Строка</th>
                      <th className="py-2 pr-4">Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importReport.errors.map((err, i) => (
                      <tr key={i} className="border-b">
                        <td className="py-2 pr-4">{err.row_number}</td>
                        <td className="py-2 pr-4">{err.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
