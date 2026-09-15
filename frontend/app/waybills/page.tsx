"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  ApiError,
  Driver,
  Trip,
  Vehicle,
  Waybill,
  createTrip,
  createWaybill,
  downloadWaybillPdf,
  generateWaybill,
  issueWaybill,
  listDrivers,
  listTrips,
  listVehicles,
  listWaybills,
} from "@/lib/api";
import { TRIP_STATUS_LABELS, WAYBILL_STATUS_LABELS } from "@/lib/labels";

function tripLabel(trip: Trip, vehicles: Vehicle[], drivers: Driver[]): string {
  const vehicle = vehicles.find((v) => v.id === trip.vehicle_id);
  const driver = drivers.find((d) => d.id === trip.driver_id);
  const date = new Date(trip.start_datetime).toLocaleDateString("ru-RU");
  return `${date} — ${vehicle?.plate_number ?? "?"} / ${driver?.full_name ?? "?"}`;
}

export default function WaybillsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [waybills, setWaybills] = useState<Waybill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showTripForm, setShowTripForm] = useState(false);
  const [tripVehicleId, setTripVehicleId] = useState("");
  const [tripDriverId, setTripDriverId] = useState("");
  const [tripStart, setTripStart] = useState("");
  const [tripEnd, setTripEnd] = useState("");
  const [tripStartLocation, setTripStartLocation] = useState("");
  const [tripEndLocation, setTripEndLocation] = useState("");
  const [tripFormError, setTripFormError] = useState<string | null>(null);
  const [tripSubmitting, setTripSubmitting] = useState(false);

  const [waybillTripId, setWaybillTripId] = useState("");
  const [documentNumber, setDocumentNumber] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [waybillFormError, setWaybillFormError] = useState<string | null>(null);
  const [waybillSubmitting, setWaybillSubmitting] = useState(false);

  const [actionErrorById, setActionErrorById] = useState<Record<string, string>>({});
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([listTrips(), listVehicles(), listDrivers(), listWaybills()])
      .then(([tripsData, vehiclesData, driversData, waybillsData]) => {
        setTrips(tripsData);
        setVehicles(vehiclesData);
        setDrivers(driversData);
        setWaybills(waybillsData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить данные"))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreateTrip(e: FormEvent) {
    e.preventDefault();
    setTripFormError(null);

    if (!tripVehicleId || !tripDriverId || !tripStart) {
      setTripFormError("Укажите автомобиль, водителя и дату начала рейса");
      return;
    }

    setTripSubmitting(true);
    try {
      const trip = await createTrip({
        vehicle_id: tripVehicleId,
        driver_id: tripDriverId,
        start_datetime: new Date(tripStart).toISOString(),
        end_datetime: tripEnd ? new Date(tripEnd).toISOString() : undefined,
        start_location: tripStartLocation.trim() || undefined,
        end_location: tripEndLocation.trim() || undefined,
      });
      setTrips((prev) => [...prev, trip]);
      setWaybillTripId(trip.id);
      setTripVehicleId("");
      setTripDriverId("");
      setTripStart("");
      setTripEnd("");
      setTripStartLocation("");
      setTripEndLocation("");
      setShowTripForm(false);
    } catch (err) {
      setTripFormError(err instanceof Error ? err.message : "Не удалось создать рейс");
    } finally {
      setTripSubmitting(false);
    }
  }

  async function handleCreateWaybill(e: FormEvent) {
    e.preventDefault();
    setWaybillFormError(null);

    if (!waybillTripId || !documentNumber.trim() || !issueDate) {
      setWaybillFormError("Укажите рейс, номер документа и дату выдачи");
      return;
    }

    setWaybillSubmitting(true);
    try {
      const waybill = await createWaybill({
        trip_id: waybillTripId,
        document_number: documentNumber.trim(),
        issue_date: issueDate,
      });
      setWaybills((prev) => [waybill, ...prev]);
      setDocumentNumber("");
      setIssueDate("");
    } catch (err) {
      setWaybillFormError(err instanceof Error ? err.message : "Не удалось создать путевой лист");
    } finally {
      setWaybillSubmitting(false);
    }
  }

  async function handleIssue(id: string) {
    setActionLoadingId(id);
    setActionErrorById((prev) => ({ ...prev, [id]: "" }));
    try {
      const updated = await issueWaybill(id);
      setWaybills((prev) => prev.map((w) => (w.id === id ? updated : w)));
    } catch (err) {
      setActionErrorById((prev) => ({
        ...prev,
        [id]: err instanceof Error ? err.message : "Не удалось выдать путевой лист",
      }));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleGenerate(id: string) {
    setActionLoadingId(id);
    setActionErrorById((prev) => ({ ...prev, [id]: "" }));
    try {
      const updated = await generateWaybill(id);
      setWaybills((prev) => prev.map((w) => (w.id === id ? updated : w)));
    } catch (err) {
      setActionErrorById((prev) => ({
        ...prev,
        [id]: err instanceof Error ? err.message : "Не удалось сгенерировать PDF",
      }));
    } finally {
      setActionLoadingId(null);
    }
  }

  async function handleDownload(waybill: Waybill) {
    setActionErrorById((prev) => ({ ...prev, [waybill.id]: "" }));
    try {
      await downloadWaybillPdf(waybill.id, `waybill-${waybill.document_number}.pdf`);
    } catch (err) {
      setActionErrorById((prev) => ({
        ...prev,
        [waybill.id]:
          err instanceof ApiError ? err.message : "Не удалось скачать PDF",
      }));
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Путевые листы</h1>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {!loading && !error && (
        <>
          <section className="mt-4 rounded border p-4">
            <h2 className="text-lg font-medium">Создать путевой лист</h2>
            <form onSubmit={handleCreateWaybill} className="mt-3 flex flex-wrap items-end gap-3">
              <div>
                <label className="block text-sm font-medium">Рейс*</label>
                <select
                  className="mt-1 rounded border px-3 py-2 text-sm"
                  value={waybillTripId}
                  onChange={(e) => setWaybillTripId(e.target.value)}
                >
                  <option value="">Выберите рейс</option>
                  {trips.map((trip) => (
                    <option key={trip.id} value={trip.id}>
                      {tripLabel(trip, vehicles, drivers)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium">Номер документа*</label>
                <input
                  type="text"
                  className="mt-1 rounded border px-3 py-2 text-sm"
                  value={documentNumber}
                  onChange={(e) => setDocumentNumber(e.target.value)}
                  placeholder="ПЛ-001"
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Дата выдачи*</label>
                <input
                  type="date"
                  className="mt-1 rounded border px-3 py-2 text-sm"
                  value={issueDate}
                  onChange={(e) => setIssueDate(e.target.value)}
                />
              </div>
              <button
                type="submit"
                disabled={waybillSubmitting}
                className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                {waybillSubmitting ? "Создание..." : "Создать"}
              </button>
              <button
                type="button"
                className="text-sm text-gray-500 underline"
                onClick={() => setShowTripForm((v) => !v)}
              >
                {showTripForm ? "Скрыть форму рейса" : "Рейса ещё нет — создать рейс"}
              </button>
            </form>
            {waybillFormError && <p className="mt-2 text-sm text-red-600">{waybillFormError}</p>}

            {showTripForm && (
              <form
                onSubmit={handleCreateTrip}
                className="mt-4 flex flex-wrap items-end gap-3 rounded border bg-gray-50 p-3"
              >
                <div>
                  <label className="block text-sm font-medium">Автомобиль*</label>
                  <select
                    className="mt-1 rounded border px-3 py-2 text-sm"
                    value={tripVehicleId}
                    onChange={(e) => setTripVehicleId(e.target.value)}
                  >
                    <option value="">Выберите автомобиль</option>
                    {vehicles.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.plate_number} ({v.brand_model})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium">Водитель*</label>
                  <select
                    className="mt-1 rounded border px-3 py-2 text-sm"
                    value={tripDriverId}
                    onChange={(e) => setTripDriverId(e.target.value)}
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
                  <label className="block text-sm font-medium">Начало рейса*</label>
                  <input
                    type="datetime-local"
                    className="mt-1 rounded border px-3 py-2 text-sm"
                    value={tripStart}
                    onChange={(e) => setTripStart(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Окончание рейса</label>
                  <input
                    type="datetime-local"
                    className="mt-1 rounded border px-3 py-2 text-sm"
                    value={tripEnd}
                    onChange={(e) => setTripEnd(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Откуда</label>
                  <input
                    type="text"
                    className="mt-1 rounded border px-3 py-2 text-sm"
                    value={tripStartLocation}
                    onChange={(e) => setTripStartLocation(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium">Куда</label>
                  <input
                    type="text"
                    className="mt-1 rounded border px-3 py-2 text-sm"
                    value={tripEndLocation}
                    onChange={(e) => setTripEndLocation(e.target.value)}
                  />
                </div>
                <button
                  type="submit"
                  disabled={tripSubmitting}
                  className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
                >
                  {tripSubmitting ? "Создание..." : "Создать рейс"}
                </button>
                {tripFormError && <p className="w-full text-sm text-red-600">{tripFormError}</p>}
              </form>
            )}
          </section>

          {waybills.length === 0 && (
            <p className="mt-4 text-sm text-gray-500">Путевые листы пока не созданы.</p>
          )}

          {waybills.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-500">
                    <th className="py-2 pr-4">Номер</th>
                    <th className="py-2 pr-4">Дата выдачи</th>
                    <th className="py-2 pr-4">Статус</th>
                    <th className="py-2 pr-4">Рейс</th>
                    <th className="py-2 pr-4">Действия</th>
                  </tr>
                </thead>
                <tbody>
                  {waybills.map((waybill) => {
                    const trip = trips.find((t) => t.id === waybill.trip_id);
                    return (
                      <tr key={waybill.id} className="border-b align-top">
                        <td className="py-2 pr-4">{waybill.document_number}</td>
                        <td className="py-2 pr-4">
                          {new Date(waybill.issue_date).toLocaleDateString("ru-RU")}
                        </td>
                        <td className="py-2 pr-4">{WAYBILL_STATUS_LABELS[waybill.status]}</td>
                        <td className="py-2 pr-4">
                          {trip
                            ? `${trip.start_location ?? "?"} → ${trip.end_location ?? "?"} (${TRIP_STATUS_LABELS[trip.status]})`
                            : waybill.trip_id}
                        </td>
                        <td className="py-2 pr-4">
                          <div className="flex flex-col items-start gap-1">
                            {waybill.status === "draft" && (
                              <button
                                type="button"
                                className="text-sm text-blue-600 underline disabled:opacity-50"
                                disabled={actionLoadingId === waybill.id}
                                onClick={() => handleIssue(waybill.id)}
                              >
                                Выдать
                              </button>
                            )}
                            {!waybill.pdf_file_url && (
                              <button
                                type="button"
                                className="text-sm text-blue-600 underline disabled:opacity-50"
                                disabled={actionLoadingId === waybill.id}
                                onClick={() => handleGenerate(waybill.id)}
                              >
                                Сгенерировать PDF
                              </button>
                            )}
                            {waybill.pdf_file_url && (
                              <button
                                type="button"
                                className="text-sm text-blue-600 underline"
                                onClick={() => handleDownload(waybill)}
                              >
                                Скачать PDF
                              </button>
                            )}
                            {actionErrorById[waybill.id] && (
                              <p className="text-xs text-red-600">{actionErrorById[waybill.id]}</p>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </main>
  );
}
