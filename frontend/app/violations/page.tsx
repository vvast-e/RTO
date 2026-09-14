"use client";

import { useCallback, useEffect, useState } from "react";

import { Driver, listDrivers, listViolations, resolveViolation, Violation } from "@/lib/api";
import { VIOLATION_SEVERITY_LABELS, VIOLATION_TYPE_LABELS, formatDateTime } from "@/lib/labels";

type ResolvedFilter = "all" | "open" | "resolved";

export default function ViolationsPage() {
  const [violations, setViolations] = useState<Violation[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [driverId, setDriverId] = useState("");
  const [resolvedFilter, setResolvedFilter] = useState<ResolvedFilter>("open");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    listViolations({
      driver_id: driverId || undefined,
      resolved: resolvedFilter === "all" ? undefined : resolvedFilter === "resolved",
    })
      .then(setViolations)
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить нарушения"))
      .finally(() => setLoading(false));
  }, [driverId, resolvedFilter]);

  useEffect(() => {
    listDrivers().then(setDrivers).catch(() => {});
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function driverName(driverIdValue: string): string {
    return drivers.find((d) => d.id === driverIdValue)?.full_name ?? driverIdValue;
  }

  async function handleResolve(id: string) {
    setResolvingId(id);
    try {
      const updated = await resolveViolation(id);
      setViolations((prev) => prev.map((v) => (v.id === id ? updated : v)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось закрыть нарушение");
    } finally {
      setResolvingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Нарушения РТО</h1>

      <div className="mt-4 flex flex-wrap items-end gap-4">
        <div>
          <label className="block text-sm font-medium">Водитель</label>
          <select
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
          >
            <option value="">Все</option>
            {drivers.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium">Статус</label>
          <select
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={resolvedFilter}
            onChange={(e) => setResolvedFilter(e.target.value as ResolvedFilter)}
          >
            <option value="open">Открытые</option>
            <option value="resolved">Закрытые</option>
            <option value="all">Все</option>
          </select>
        </div>
      </div>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && violations.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">Нарушений не найдено.</p>
      )}

      {!loading && !error && violations.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 pr-4">Тип</th>
                <th className="py-2 pr-4">Серьёзность</th>
                <th className="py-2 pr-4">Обнаружено</th>
                <th className="py-2 pr-4">Водитель</th>
                <th className="py-2 pr-4">Статус</th>
                <th className="py-2 pr-4" />
              </tr>
            </thead>
            <tbody>
              {violations.map((v) => (
                <tr key={v.id} className="border-b">
                  <td className="py-2 pr-4">{VIOLATION_TYPE_LABELS[v.violation_type]}</td>
                  <td className="py-2 pr-4">
                    <span
                      className={
                        v.severity === "violation"
                          ? "text-red-600"
                          : "text-amber-600"
                      }
                    >
                      {VIOLATION_SEVERITY_LABELS[v.severity]}
                    </span>
                  </td>
                  <td className="py-2 pr-4">{formatDateTime(v.detected_at)}</td>
                  <td className="py-2 pr-4">{driverName(v.driver_id)}</td>
                  <td className="py-2 pr-4">{v.resolved ? "Закрыто" : "Открыто"}</td>
                  <td className="py-2 pr-4">
                    {!v.resolved && (
                      <button
                        type="button"
                        disabled={resolvingId === v.id}
                        onClick={() => handleResolve(v.id)}
                        className="text-sm text-gray-900 underline disabled:opacity-50"
                      >
                        {resolvingId === v.id ? "..." : "Закрыть"}
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
