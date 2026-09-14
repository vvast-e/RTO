"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getAccessToken } from "@/lib/auth";

const PUBLIC_PATHS = ["/login"];

/**
 * Layout-guard: редиректит на /login, если в localStorage нет access-токена.
 * Полноценная проверка валидности/срока токена на сервере — при первом
 * запросе к API (401 там обрабатывается отдельно); здесь только факт
 * наличия токена, чтобы не пускать на защищённые страницы совсем без входа.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (PUBLIC_PATHS.includes(pathname)) {
      setChecked(true);
      return;
    }
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    setChecked(true);
  }, [pathname, router]);

  if (!checked) return null;
  return <>{children}</>;
}
