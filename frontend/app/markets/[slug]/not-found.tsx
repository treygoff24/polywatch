export default function MarketNotFound() {
  return (
    <main className="mx-auto flex min-h-[60vh] max-w-3xl flex-col items-center justify-center gap-4 px-6 text-center">
      <h1 className="font-display text-4xl text-white">Market unavailable</h1>
      <p className="text-slate-300">
        We don&apos;t have a cached snapshot for this slug yet. Run the exporter or
        check the spelling.
      </p>
    </main>
  );
}

