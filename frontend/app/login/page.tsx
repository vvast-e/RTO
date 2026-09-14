"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  confirmLogin,
  confirmRegister,
  requestLoginCode,
  requestRegisterCode,
} from "@/lib/api";
import { setTokens } from "@/lib/auth";

type Mode = "login" | "register";
type Step = "phone" | "code";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<Mode>("login");
  const [step, setStep] = useState<Step>("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [userName, setUserName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleRequestCode(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "register") {
        await requestRegisterCode(phone);
      } else {
        await requestLoginCode(phone);
      }
      setStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить код");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirmCode(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens =
        mode === "register"
          ? await confirmRegister(phone, code, organizationName, userName)
          : await confirmLogin(phone, code);
      setTokens(tokens);
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось подтвердить код");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-md p-4 sm:max-w-lg">
      <h1 className="text-2xl font-semibold">
        {mode === "register" ? "Регистрация организации" : "Вход"}
      </h1>

      <div className="mt-4 flex gap-2 text-sm">
        <button
          type="button"
          className={mode === "login" ? "font-semibold underline" : "text-gray-500"}
          onClick={() => {
            setMode("login");
            setStep("phone");
            setError(null);
          }}
        >
          Вход
        </button>
        <span className="text-gray-300">/</span>
        <button
          type="button"
          className={mode === "register" ? "font-semibold underline" : "text-gray-500"}
          onClick={() => {
            setMode("register");
            setStep("phone");
            setError(null);
          }}
        >
          Регистрация
        </button>
      </div>

      {step === "phone" && (
        <form className="mt-6 space-y-4" onSubmit={handleRequestCode}>
          <div>
            <label className="block text-sm font-medium">Телефон</label>
            <input
              type="tel"
              required
              placeholder="+79991234567"
              className="mt-1 w-full rounded border px-3 py-2"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          {mode === "register" && (
            <>
              <div>
                <label className="block text-sm font-medium">Название организации</label>
                <input
                  type="text"
                  required
                  className="mt-1 w-full rounded border px-3 py-2"
                  value={organizationName}
                  onChange={(e) => setOrganizationName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-medium">Ваше имя</label>
                <input
                  type="text"
                  required
                  className="mt-1 w-full rounded border px-3 py-2"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                />
              </div>
            </>
          )}
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-gray-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {loading ? "Отправка..." : "Получить код"}
          </button>
        </form>
      )}

      {step === "code" && (
        <form className="mt-6 space-y-4" onSubmit={handleConfirmCode}>
          <p className="text-sm text-gray-600">Код отправлен на {phone}</p>
          <div>
            <label className="block text-sm font-medium">Код из SMS</label>
            <input
              type="text"
              required
              inputMode="numeric"
              className="mt-1 w-full rounded border px-3 py-2"
              value={code}
              onChange={(e) => setCode(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded bg-gray-900 px-4 py-2 text-white disabled:opacity-50"
          >
            {loading ? "Проверка..." : "Подтвердить"}
          </button>
          <button
            type="button"
            className="w-full text-sm text-gray-500 underline"
            onClick={() => setStep("phone")}
          >
            Изменить номер
          </button>
        </form>
      )}
    </main>
  );
}
