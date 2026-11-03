import { es } from "../i18n/es";

export function NotFoundPage() {
  return (
    <main className="flex min-h-dvh flex-col items-center justify-center gap-6 p-4 text-center">
      <h1 className="text-3xl font-bold">{es.notFound.title}</h1>
      <a
        href="/map"
        className="inline-flex min-h-11 items-center rounded-lg bg-accent px-6 font-semibold text-white"
      >
        {es.notFound.goToMap}
      </a>
    </main>
  );
}
