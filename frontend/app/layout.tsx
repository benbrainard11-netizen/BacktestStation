import type { Metadata } from "next";

import { AppearanceProvider } from "@/components/AppearanceProvider";
import { AppShell } from "@/components/layout/AppShell";

import "./globals.css";

export const metadata: Metadata = {
  title: "BacktestStation",
  description: "Futures strategy research terminal",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppearanceProvider>
          <AppShell>{children}</AppShell>
        </AppearanceProvider>
      </body>
    </html>
  );
}
