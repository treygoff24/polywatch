'use client';

import { useEffect, useMemo, useState } from "react";

type LocalizedTimeProps = {
  value: string | number | Date | null | undefined;
  options?: Intl.DateTimeFormatOptions;
  fallback?: string;
  className?: string;
};

const DEFAULT_OPTIONS: Intl.DateTimeFormatOptions = {
  dateStyle: "medium",
  timeStyle: "short"
};

export default function LocalizedTime({
  value,
  options,
  fallback = "n/a",
  className
}: LocalizedTimeProps) {
  const isoValue = useMemo(() => {
    if (value == null) {
      return null;
    }
    const date =
      typeof value === "string" || value instanceof Date
        ? new Date(value)
        : new Date(value);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date.toISOString();
  }, [value]);

  const [display, setDisplay] = useState<string>(() =>
    isoValue ?? fallback
  );

  useEffect(() => {
    if (!isoValue) {
      setDisplay(fallback);
      return;
    }
    const formatter = new Intl.DateTimeFormat(undefined, options ?? DEFAULT_OPTIONS);
    setDisplay(formatter.format(new Date(isoValue)));
  }, [isoValue, options, fallback]);

  if (!isoValue) {
    return (
      <span className={className} suppressHydrationWarning>
        {fallback}
      </span>
    );
  }

  return (
    <time
      suppressHydrationWarning
      dateTime={isoValue}
      className={className}
    >
      {display}
    </time>
  );
}
