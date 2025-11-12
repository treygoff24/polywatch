import type { Metadata } from "next";
import { Inter, Rajdhani } from "next/font/google";
import "./globals.css";

const display = Rajdhani({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display"
});

const body = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body"
});

export const metadata: Metadata = {
  title: "Polywatch | Polymarket Anomaly Radar",
  description:
    "Cyberpunk analytics for Polymarket — scan markets, surface anomalies, and investigate suspicious flow.",
  metadataBase: new URL("https://polywatch.example"),
  openGraph: {
    title: "Polywatch",
    description:
      "Cyberpunk analytics for Polymarket — scan markets, surface anomalies, and investigate suspicious flow.",
    url: "https://polywatch.example",
    siteName: "Polywatch",
    images: [
      {
        url: "https://polywatch.example/og.png",
        width: 1200,
        height: 630,
        alt: "Polywatch cyberpunk dashboard preview"
      }
    ]
  },
  twitter: {
    card: "summary_large_image",
    title: "Polywatch",
    description:
      "Cyberpunk analytics for Polymarket — scan markets, surface anomalies, and investigate suspicious flow.",
    creator: "@polywatch"
  }
};

export default function RootLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${body.variable}`}
      suppressHydrationWarning
    >
      <body className="bg-night-900 text-slate-100 antialiased min-h-screen">
        <div className="relative isolate overflow-hidden">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(0,245,255,0.18),_transparent_55%)]" />
          <div className="relative z-10">{children}</div>
        </div>
      </body>
    </html>
  );
}

