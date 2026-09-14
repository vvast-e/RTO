import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "РТО-аналитика",
  description: "Учёт РТО и путевых листов для малых автоперевозчиков",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru">
      <body className="min-h-screen bg-gray-50 text-gray-900">{children}</body>
    </html>
  );
}
