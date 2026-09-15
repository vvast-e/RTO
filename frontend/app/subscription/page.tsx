"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  Subscription,
  SubscriptionPlan,
  getSubscription,
  updateSubscription,
} from "@/lib/api";
import { SUBSCRIPTION_PLAN_LABELS, SUBSCRIPTION_STATUS_LABELS } from "@/lib/labels";

const PLAN_DEFAULT_LIMITS: Record<SubscriptionPlan, number> = {
  starter: 3,
  pro: 10,
  fleet: 30,
};

export default function SubscriptionPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [plan, setPlan] = useState<SubscriptionPlan>("starter");
  const [vehiclesLimit, setVehiclesLimit] = useState(3);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    getSubscription()
      .then((sub) => {
        setSubscription(sub);
        setPlan(sub.plan);
        setVehiclesLimit(sub.vehicles_limit);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить подписку"))
      .finally(() => setLoading(false));
  }, []);

  async function handleUpgrade(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      const updated = await updateSubscription({
        plan,
        vehicles_limit: vehiclesLimit,
        status: "active",
      });
      setSubscription(updated);
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Не удалось обновить подписку");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-4xl p-4">
      <h1 className="text-2xl font-semibold">Подписка</h1>

      {loading && <p className="mt-4 text-sm text-gray-500">Загрузка...</p>}
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {subscription && (
        <div className="mt-4 rounded border p-4">
          <dl className="grid grid-cols-2 gap-y-2 text-sm sm:grid-cols-4">
            <dt className="text-gray-500">Тариф</dt>
            <dd className="font-medium">{SUBSCRIPTION_PLAN_LABELS[subscription.plan]}</dd>
            <dt className="text-gray-500">Статус</dt>
            <dd className={`font-medium ${subscription.status === "expired" ? "text-red-600" : ""}`}>
              {SUBSCRIPTION_STATUS_LABELS[subscription.status]}
            </dd>
            <dt className="text-gray-500">Автомобили</dt>
            <dd className="font-medium">
              {subscription.vehicles_used} из {subscription.vehicles_limit}
            </dd>
            <dt className="text-gray-500">Стоимость</dt>
            <dd className="font-medium">{subscription.price} ₽/мес</dd>
            {subscription.next_billing_date && (
              <>
                <dt className="text-gray-500">Следующее списание</dt>
                <dd className="font-medium">{subscription.next_billing_date}</dd>
              </>
            )}
          </dl>
        </div>
      )}

      {subscription && (
        <div className="mt-6 rounded border p-4">
          <h2 className="text-lg font-semibold">Изменить тариф</h2>
          <p className="mt-1 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Это эмуляция апгрейда для MVP — реального платежа не происходит,
            изменения применяются сразу и бесплатно. Интеграция с реальным
            платёжным провайдером (ЮKassa) ещё не подключена.
          </p>

          <form onSubmit={handleUpgrade} className="mt-4 flex flex-wrap items-end gap-3">
            <div>
              <label className="block text-sm font-medium">Тариф</label>
              <select
                className="mt-1 rounded border px-3 py-2 text-sm"
                value={plan}
                onChange={(e) => {
                  const nextPlan = e.target.value as SubscriptionPlan;
                  setPlan(nextPlan);
                  setVehiclesLimit(PLAN_DEFAULT_LIMITS[nextPlan]);
                }}
              >
                {Object.entries(SUBSCRIPTION_PLAN_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium">Лимит автомобилей</label>
              <input
                type="number"
                min={subscription.vehicles_used}
                className="mt-1 w-28 rounded border px-3 py-2 text-sm"
                value={vehiclesLimit}
                onChange={(e) => setVehiclesLimit(Number(e.target.value))}
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="rounded bg-gray-900 px-4 py-2 text-sm text-white disabled:opacity-50"
            >
              {submitting ? "Применение..." : "Применить (эмуляция)"}
            </button>
            {formError && <p className="w-full text-sm text-red-600">{formError}</p>}
          </form>
        </div>
      )}
    </main>
  );
}
