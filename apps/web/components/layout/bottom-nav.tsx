"use client";

import { Bookmark, House, Network, Search, User } from "lucide-react";
import { usePathname } from "next/navigation";

const items = [
  { icon: House,    label: "Home",    href: "/"      },
  { icon: Search,   label: "Explore", href: "#"      },
  { icon: Network,  label: "Graph",   href: "/graph" },
  { icon: Bookmark, label: "Saved",   href: "#"      },
  { icon: User,     label: "Profile", href: "#"      },
];

export function BottomNav() {
  const pathname = usePathname();
  return (
    <nav
      className="bottom-nav-mobile"
      style={{
        position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 50,
        height: 56,
        display: "flex", alignItems: "center", justifyContent: "space-around",
        borderTop: "1px solid var(--border)",
        background: "var(--bg)",
      }}
    >
      {items.map(({ icon: Icon, label, href }) => {
        const active = href !== "#" && pathname === href;
        return (
          <a
            key={label}
            href={href}
            aria-label={label}
            style={{
              display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
              padding: "6px 12px",
              color: active ? "var(--text)" : "var(--text-muted)",
              fontSize: 10, letterSpacing: "0.03em",
              textDecoration: "none",
            }}
          >
            <Icon size={20} strokeWidth={active ? 2.5 : 2} />
            {label}
          </a>
        );
      })}
    </nav>
  );
}
