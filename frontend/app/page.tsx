"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { Driver, Violation, listDrivers, listViolations } from "@/lib/api";

type DriverStatus = "red" | "yellow" | "green";

const STATUS_STYLES: Record<DriverStatus, { dot: string; label: string; row: string }> = {
  red: { dot: "bg-red-600", label: "Нарушение", row: "hover:bg-red-50" },
  yellow: { dot: "bg-amber-500", label: "Предупреждение", row: "hover:bg-amber-50" },
  green: { dot: "bg-green-600", label: "Норма", row: "hover:bg-green-50" },
};

export default function HomePage() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [openViolations, setOpenViolations] = useState<Violation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([listDrivers(), listViolations({ resolved: false })])
      .then(([driverList, violationList]) => {
        setDrivers(driverList);
        setOpenViolations(violationList);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить данные"))
      .finally(() => setLoading(false));
  }, []);

  const violationsByDriver = useMemo(() => {
    const map = new Map<string, Violation[]>();
    for (const v of openViolations) {
      const list = map.get(v.driver_id);
      if (list) list.push(v);
      else map.set(v.driver_id, [v]);
    }
    return map;
  }, [openViolations]);

  const rows = useMemo(() => {
    return drivers
      .map((driver) => {
        const driverViolations = violationsByDriver.get(driver.id) ?? [];
        const violationCount = driverViolations.filter((v) => v.severity === "violation").length;
        const warningCount = driverViolations.filter((v) => v.severity === "warning").length;
        const status: DriverStatus = violationCount > 0 ? "red" : warningCount > 0 ? "yellow" : "green";
        return { driver, status, violationCount, warningCount };
      })
      .sort((a, b) => {
        const order: Record<DriverStatus, number> = { red: 0, yellow: 1, green: 2 };
        return order[a.status] - order[b.status];
      });
  }, [drivers, violationsByDriver]);

  const summary = useMemo(() => {
    return rows.reduce(
      (acc, row) => {
        acc[row.status] += 1;
        return acc;
      },
      { red: 0, yellow: 0, green: 0 } as Record<DriverStatus, number>
    );
  }, [rows]);

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">РТО-аналитика</h1>
      <p className="mt-2 text-sm text-gray-600">Статус режима труда и отдыха по водителям.</p>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <>
          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded border p-3">
              <div className="text-xs text-gray-500">Всего водителей</div>
              <div className="mt-1 text-xl font-semibold">{drivers.length}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-xs text-gray-500">🔴 Нарушения</div>
              <div className="mt-1 text-xl font-semibold text-red-600">{summary.red}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-xs text-gray-500">🟡 Предупреждения</div>
              <div className="mt-1 text-xl font-semibold text-amber-600">{summary.yellow}</div>
            </div>
            <div className="rounded border p-3">
              <div className="text-xs text-gray-500">🟢 В норме</div>
              <div className="mt-1 text-xl font-semibold text-green-600">{summary.green}</div>
            </div>
          </div>

          {rows.length === 0 ? (
            <p className="mt-6 text-sm text-gray-500">Водителей пока нет.</p>
          ) : (
            <div className="mt-6 overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2 pr-4">Статус</th>
                    <th className="py-2 pr-4">Водитель</th>
                    <th className="py-2 pr-4">Открытых нарушений</th>
                    <th className="py-2 pr-4">Предупреждений</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map(({ driver, status, violationCount, warningCount }) => (
                    <tr key={driver.id} className={`border-b ${STATUS_STYLES[status].row}`}>
                      <td className="py-2 pr-4">
                        <Link
                          href={`/violations?driver_id=${driver.id}`}
                          className="flex items-center gap-2"
                          title={STATUS_STYLES[status].label}
                        >
                          <span className={`inline-block h-3 w-3 rounded-full ${STATUS_STYLES[status].dot}`} />
                        </Link>
                      </td>
                      <td className="py-2 pr-4">
                        <Link href={`/violations?driver_id=${driver.id}`} className="underline">
                          {driver.full_name}
                        </Link>
                      </td>
                      <td className="py-2 pr-4">{violationCount}</td>
                      <td className="py-2 pr-4">{warningCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </main>
  );
}
