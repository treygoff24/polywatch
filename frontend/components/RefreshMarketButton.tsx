'use client';

import clsx from "clsx";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";

interface RefreshMarketButtonProps {
  slug: string;
  className?: string;
}

export default function RefreshMarketButton({
  slug,
  className
}: RefreshMarketButtonProps) {
  const router = useRouter();
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "done">(
    "idle"
  );
  const [message, setMessage] = useState<string | null>(null);

  async function refreshReport() {
    setStatus("loading");
    setMessage(null);
    try {
      const response = await fetch(`/api/live-reports/${slug}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error ?? "Refresh failed");
      }
      setStatus("done");
      router.refresh();
      setTimeout(() => setStatus("idle"), 1500);
    } catch (error) {
      setStatus("error");
      setMessage((error as Error).message);
    }
  }

  const label =
    status === "loading"
      ? "Refreshing…"
      : status === "done"
        ? "Fresh report ready"
        : "Refresh report";

  return (
    <div className={clsx("flex flex-col gap-2", className)}>
      <button
        type="button"
        onClick={refreshReport}
        disabled={status === "loading"}
        className="inline-flex items-center gap-2 rounded-full border border-neon-cyan/60 px-5 py-2 text-sm font-semibold text-white transition hover:border-neon-cyan hover:bg-neon-cyan/10 disabled:opacity-60"
      >
        {status === "loading" ? (
          <Loader2 className="h-4 w-4 animate-spin text-neon-cyan" />
        ) : null}
        {label}
      </button>
      {message ? (
        <p className="text-xs text-red-300">{message}</p>
      ) : null}
    </div>
  );
}
