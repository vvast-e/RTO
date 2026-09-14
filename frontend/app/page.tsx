export default function HomePage() {
  return (
    <main className="mx-auto max-w-md p-4 sm:max-w-2xl">
      <h1 className="text-2xl font-semibold">РТО-аналитика</h1>
      <p className="mt-2 text-sm text-gray-600">
        Учёт автопарка, режима труда и отдыха водителей, путевые листы.
      </p>
      {/* TODO: онбординг-флоу (добавить машину → добавить водителя → первый рейс),
          дашборд-светофор, формы ввода рабочего времени — Спринт 1–3 */}
    </main>
  );
}
