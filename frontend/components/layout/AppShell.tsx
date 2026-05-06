"use client";

import { usePathname } from "next/navigation";

import { SubNav } from "./SubNav";
import { TopTabs } from "./TopTabs";

/**
 * App chrome — top tabs row → horizontal sub-nav → scrolling main content.
 * No sidebar, no footer status bar; design uses `app-tabbed` mode and surfaces
 * live status via the meta strip in TopTabs.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return (
    <div className="app">
      <main className="app-main">
        <TopTabs />
        <SubNav pathname={pathname} />
        <div className="app-content">{children}</div>
      </main>
    </div>
  );
}
