"use client";

import { useEffect, useState } from "react";

import { Driver, listDrivers } from "@/lib/api";
import { formatDateTime } from "@/lib/labels";

export default function DriversPage() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listDrivers()
      .then(setDrivers)
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить водителей"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Водители</h1>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && drivers.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">Водители пока не добавлены.</p>
      )}

      {!loading && !error && drivers.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 pr-4">ФИО</th>
                <th className="py-2 pr-4">Номер карты тахографа</th>
                <th className="py-2 pr-4">Добавлен</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((driver) => (
                <tr key={driver.id} className="border-b">
                  <td className="py-2 pr-4">{driver.full_name}</td>
                  <td className="py-2 pr-4">{driver.tachograph_card_number ?? "—"}</td>
                  <td className="py-2 pr-4">{formatDateTime(driver.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
