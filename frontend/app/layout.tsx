import type { Metadata } from "next";
import { Work_Sans } from "next/font/google";

import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

import "./globals.css";

const workSans = Work_Sans({
  subsets: ["latin"],
  variable: "--font-work-sans",
});

export const metadata: Metadata = {
  title: "BacktestStation",
  description: "Futures strategy research terminal",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={workSans.variable}>
      <body className="min-h-screen bg-zinc-950 text-zinc-100">
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex min-h-screen flex-1 flex-col overflow-hidden">
            <TopBar />
            <main className="flex-1 overflow-auto">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
