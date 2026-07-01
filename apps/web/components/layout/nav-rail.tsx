"use client";

import {
  Bell, Bookmark, House, MoreHorizontal, Network,
  Search, Upload, User,
} from "lucide-react";
import { usePathname } from "next/navigation";

const items = [
  { icon: House,       label: "Home",          href: "/"       },
  { icon: Search,      label: "Explore",        href: "#"       },
  { icon: Network,     label: "Graph",          href: "/graph"  },
  { icon: Upload,      label: "Ingest",         href: "/ingest" },
  { icon: Bell,        label: "Notifications",  href: "#"       },
  { icon: Bookmark,    label: "Bookmarks",      href: "#"       },
  { icon: User,        label: "Profile",        href: "#"       },
  { icon: MoreHorizontal, label: "More",        href: "#"       },
];

export function NavRail() {
  const pathname = usePathname();
  return (
    <nav style={{
      width: 275, flexShrink: 0,
      display: "flex", flexDirection: "column",
      padding: "8px 12px 20px",
      height: "100%", overflowY: "auto",
      scrollbarWidth: "none",
    }}
    className="hidden md:flex"
    >
      {/* Logo */}
      <a href="/" style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        width: 48, height: 48, borderRadius: 99, marginBottom: 4,
        textDecoration: "none", transition: "background 0.12s",
      }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-2)")}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
      >
        <span style={{ fontSize: 22, fontWeight: 900, letterSpacing: "-0.05em", color: "var(--text)" }}>lg</span>
      </a>

      {/* Nav items */}
      <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
        {items.map(({ icon: Icon, label, href }) => {
          const active = href !== "#" && pathname === href;
          return (
            <a
              key={label}
              href={href}
              className={`nav-item-rail${active ? " active" : ""}`}
            >
              <Icon size={26} strokeWidth={active ? 2.5 : 2} />
              <span>{label}</span>
            </a>
          );
        })}
      </div>

      {/* Post button */}
      <button style={{
        marginTop: 16,
        width: "100%", padding: "14px 0",
        borderRadius: 99, border: "none",
        background: "var(--text)", color: "var(--bg)",
        fontSize: 17, fontWeight: 700, cursor: "pointer",
        transition: "opacity 0.15s",
      }}
      onMouseEnter={e => (e.currentTarget.style.opacity = "0.88")}
      onMouseLeave={e => (e.currentTarget.style.opacity = "1")}
      >
        Post
      </button>

      {/* Account */}
      <div style={{
        marginTop: "auto",
        display: "flex", alignItems: "center", gap: 12,
        padding: "12px 16px", borderRadius: 99, cursor: "pointer",
        transition: "background 0.12s",
      }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--surface-2)")}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
      >
        <div style={{
          width: 40, height: 40, borderRadius: "50%",
          background: "var(--surface-2)",
          border: "1px solid var(--border-strong)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 15, fontWeight: 700, color: "var(--text-muted)",
          flexShrink: 0,
        }}>
          K
        </div>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", lineHeight: 1.2 }}>Keno</div>
          <div style={{ fontSize: 14, color: "var(--text-muted)", lineHeight: 1.2 }}>@keno</div>
        </div>
        <MoreHorizontal size={18} style={{ marginLeft: "auto", color: "var(--text-muted)", flexShrink: 0 }} />
      </div>
    </nav>
  );
}
