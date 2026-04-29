import type { Metadata } from "next";
import { Work_Sans } from "next/font/google";

import CommandPalette from "@/components/layout/CommandPalette";
import ContextBar from "@/components/layout/ContextBar";
import KeyboardHelp from "@/components/layout/KeyboardHelp";
import TopBar from "@/components/layout/TopBar";
import TopTabs from "@/components/layout/TopTabs";

import "./globals.css";

const workSans = Work_Sans({
 subsets: ["latin"],
 // Pull the full weight range so the tearsheet view can use 200 light
 // for display + 700+ for emphasis without falling back to faux weights.
 weight: ["200", "300", "400", "500", "600", "700", "800", "900"],
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
 <body className="min-h-screen bg-bg text-text">
 <div className="flex h-screen flex-col overflow-hidden">
 <TopBar />
 <TopTabs />
 <main className="flex-1 overflow-auto bg-bg">
 {children}
 </main>
 <ContextBar />
 </div>
 <CommandPalette />
 <KeyboardHelp />
 </body>
 </html>
 );
}
