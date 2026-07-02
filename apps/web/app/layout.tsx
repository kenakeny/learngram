import type { Metadata } from "next";
import "./globals.css";
import { NavRail } from "@/components/layout/nav-rail";
import { BottomNav } from "@/components/layout/bottom-nav";
import { RightSidebar } from "@/components/layout/right-sidebar";

export const metadata: Metadata = {
  title: "learngram",
  description: "Productive doom-scrolling through technical concepts",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ display: "flex", height: "100%", overflow: "hidden" }}>
        <NavRail />
        <div style={{ flex: 1, display: "flex", minWidth: 0, overflow: "hidden" }}>
          {/* Center column */}
          <main style={{
            flex: 1,
            position: "relative",
            minWidth: 0,
            overflow: "hidden",
            borderLeft: "1px solid var(--border)",
            borderRight: "1px solid var(--border)",
          }}>
            {children}
          </main>
          <RightSidebar />
        </div>
        <BottomNav />
      </body>
    </html>
  );
}
