"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { clearTokens } from "@/lib/auth";

const LINKS = [
  { href: "/", label: "Главная" },
  { href: "/drivers", label: "Водители" },
  { href: "/vehicles", label: "Автомобили" },
  { href: "/worktime", label: "Рабочее время" },
  { href: "/violations", label: "Нарушения" },
  { href: "/reminders", label: "Напоминания" },
];

export default function NavBar() {
  const pathname = usePathname();
  const router = useRouter();

  if (pathname === "/login") return null;

  return (
    <header className="border-b bg-white">
      <nav className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <div className="flex gap-4 text-sm">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={
                pathname === link.href
                  ? "font-semibold underline"
                  : "text-gray-500 hover:text-gray-900"
              }
            >
              {link.label}
            </Link>
          ))}
        </div>
        <button
          type="button"
          className="text-sm text-gray-500 underline"
          onClick={() => {
            clearTokens();
            router.replace("/login");
          }}
        >
          Выйти
        </button>
      </nav>
    </header>
  );
}
