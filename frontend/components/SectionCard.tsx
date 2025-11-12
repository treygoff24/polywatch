import clsx from "clsx";
import { ReactNode } from "react";

interface SectionCardProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function SectionCard({
  title,
  subtitle,
  action,
  children,
  className
}: SectionCardProps) {
  return (
    <section
      className={clsx(
        "glass-panel rounded-3xl p-6 md:p-8 overflow-hidden border border-white/10",
        "shadow-[0_0_50px_rgba(0,245,255,0.12)]",
        className
      )}
    >
      <header className="mb-6 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-display text-2xl tracking-widest uppercase text-white">
            {title}
          </h2>
          {subtitle ? (
            <p className="text-sm text-slate-300/80">{subtitle}</p>
          ) : null}
        </div>
        {action ? <div className="text-sm text-slate-200">{action}</div> : null}
      </header>
      <div>{children}</div>
    </section>
  );
}

