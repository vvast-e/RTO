"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Subscription, getSubscription } from "@/lib/api";
import { SUBSCRIPTION_PLAN_LABELS, SUBSCRIPTION_STATUS_LABELS } from "@/lib/labels";

export default function SubscriptionBanner() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);

  useEffect(() => {
    getSubscription()
      .then(setSubscription)
      .catch(() => {
        // Баннер необязателен для работы страницы — молча скрываем при ошибке
        // загрузки (например, у организации ещё нет подписки).
      });
  }, []);

  if (!subscription) return null;

  const isExpired = subscription.status === "expired";

  return (
    <Link
      href="/subscription"
      className={`mt-4 flex flex-wrap items-center justify-between gap-2 rounded border px-4 py-2 text-sm ${
        isExpired ? "border-red-300 bg-red-50 text-red-800" : "border-gray-200 bg-gray-50 text-gray-700"
      }`}
    >
      <span>
        Тариф <strong>{SUBSCRIPTION_PLAN_LABELS[subscription.plan]}</strong> ·{" "}
        {isExpired ? "⚠ " : ""}
        {SUBSCRIPTION_STATUS_LABELS[subscription.status]} · используется{" "}
        {subscription.vehicles_used} из {subscription.vehicles_limit} машин
      </span>
      <span className="underline">Управление подпиской →</span>
    </Link>
  );
}
