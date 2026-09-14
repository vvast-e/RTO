"use client";

import { FormEvent, useEffect, useState } from "react";

import { createDriver, Driver, listDrivers } from "@/lib/api";
import { formatDateTime } from "@/lib/labels";

export default function DriversPage() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [licenseNumber, setLicenseNumber] = useState("");
  const [cardNumber, setCardNumber] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listDrivers()
      .then(setDrivers)
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить водителей"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!fullName.trim()) {
      setFormError("Укажите ФИО водителя");
      return;
    }
    setSubmitting(true);
    try {
      const driver = await createDriver({
        full_name: fullName.trim(),
        phone: phone.trim() || undefined,
        license_number: licenseNumber.trim() || undefined,
        tachograph_card_number: cardNumber.trim() || undefined,
      });
      setDrivers((prev) => [...prev, driver]);
      setFullName("");
      setPhone("");
      setLicenseNumber("");
      setCardNumber("");
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Не удалось добавить водителя");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Водители</h1>

      <form
        onSubmit={handleSubmit}
        className="mt-4 flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <div>
          <label className="block text-sm font-medium">ФИО*</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Телефон</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Номер прав</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={licenseNumber}
            onChange={(e) => setLicenseNumber(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Номер карты тахографа</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={cardNumber}
            onChange={(e) => setCardNumber(e.target.value)}
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
