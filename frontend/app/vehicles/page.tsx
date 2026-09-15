"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { ApiError, createVehicle, listVehicles, updateVehicle, Vehicle, VehicleStatus } from "@/lib/api";
import { VEHICLE_STATUS_LABELS } from "@/lib/labels";

// Дублирует backend-regex (app/schemas/vehicle.py) для быстрой клиентской
// проверки — финальная валидация всё равно на backend.
const PLATE_RE = /^[АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3}$/i;

export default function VehiclesPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [plateNumber, setPlateNumber] = useState("");
  const [brandModel, setBrandModel] = useState("");
  const [tachographType, setTachographType] = useState("");
  const [status, setStatus] = useState<VehicleStatus>("active");
  const [nextInspectionDate, setNextInspectionDate] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [subscriptionBlocked, setSubscriptionBlocked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [dateSavingId, setDateSavingId] = useState<string | null>(null);

  useEffect(() => {
    listVehicles()
      .then(setVehicles)
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить автомобили"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubscriptionBlocked(false);

    const normalizedPlate = plateNumber.trim().toUpperCase().replace(/\s+/g, "");
    if (!normalizedPlate) {
      setFormError("Укажите гос. номер");
      return;
    }
    if (!PLATE_RE.test(normalizedPlate)) {
      setFormError("Некорректный формат гос. номера РФ (например, А000АА00)");
      return;
    }
    if (!brandModel.trim()) {
      setFormError("Укажите марку и модель");
      return;
    }

    setSubmitting(true);
    try {
      const vehicle = await createVehicle({
        plate_number: normalizedPlate,
        brand_model: brandModel.trim(),
        tachograph_type: tachographType.trim() || undefined,
        status,
        next_inspection_date: nextInspectionDate || undefined,
      });
      setVehicles((prev) => [...prev, vehicle]);
      setPlateNumber("");
      setBrandModel("");
      setTachographType("");
      setStatus("active");
      setNextInspectionDate("");
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) {
        setSubscriptionBlocked(true);
      }
      setFormError(err instanceof Error ? err.message : "Не удалось добавить автомобиль");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleInspectionDateChange(vehicleId: string, value: string) {
    setDateSavingId(vehicleId);
    try {
      const updated = await updateVehicle(vehicleId, {
        next_inspection_date: value || null,
      });
      setVehicles((prev) => prev.map((v) => (v.id === vehicleId ? updated : v)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось обновить дату ТО");
    } finally {
      setDateSavingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Автомобили</h1>

      <form
        onSubmit={handleSubmit}
        className="mt-4 flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <div>
          <label className="block text-sm font-medium">Гос. номер*</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={plateNumber}
            onChange={(e) => setPlateNumber(e.target.value)}
            placeholder="А000АА00"
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Марка/модель*</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={brandModel}
            onChange={(e) => setBrandModel(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Тип тахографа</label>
          <input
            type="text"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={tachographType}
            onChange={(e) => setTachographType(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium">Статус</label>
          <select
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={status}
            onChange={(e) => setStatus(e.target.value as VehicleStatus)}
          >
            {Object.entries(VEHICLE_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium">Дата след. ТО</label>
          <input
            type="date"
            className="mt-1 rounded border px-3 py-2 text-sm"
            value={nextInspectionDate}
            onChange={(e) => setNextInspectionDate(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {submitting ? "Добавление..." : "Добавить"}
        </button>
        {formError && (
          <p className="w-full text-sm text-red-600">
            {formError}
            {subscriptionBlocked && (
              <>
                {" "}
                <Link href="/subscription" className="underline">
                  Перейти к управлению подпиской
                </Link>
              </>
            )}
          </p>
        )}
      </form>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && vehicles.length === 0 && (
        <p className="mt-4 text-sm text-gray-500">Автомобили пока не добавлены.</p>
      )}

      {!loading && !error && vehicles.length > 0 && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="py-2 pr-4">Гос. номер</th>
                <th className="py-2 pr-4">Марка/модель</th>
                <th className="py-2 pr-4">Тип тахографа</th>
                <th className="py-2 pr-4">Статус</th>
                <th className="py-2 pr-4">Дата след. ТО</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map((vehicle) => (
                <tr key={vehicle.id} className="border-b">
                  <td className="py-2 pr-4">{vehicle.plate_number}</td>
                  <td className="py-2 pr-4">{vehicle.brand_model}</td>
                  <td className="py-2 pr-4">{vehicle.tachograph_type ?? "—"}</td>
                  <td className="py-2 pr-4">{VEHICLE_STATUS_LABELS[vehicle.status]}</td>
                  <td className="py-2 pr-4">
                    <input
                      type="date"
                      className="rounded border px-2 py-1 text-sm"
                      value={vehicle.next_inspection_date ?? ""}
                      disabled={dateSavingId === vehicle.id}
                      onChange={(e) => handleInspectionDateChange(vehicle.id, e.target.value)}
                    />
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
