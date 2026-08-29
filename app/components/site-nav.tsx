"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { getToken, setToken } from "@/lib/api";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/clients", label: "Clients" },
  { href: "/connectors", label: "Connectors" },
  { href: "/models", label: "Models" },
  { href: "/optimize", label: "Optimize" },
  { href: "/reports", label: "Reports" },
  { href: "/onboarding", label: "Onboarding" },
  { href: "/settings", label: "Settings" },
];

export function SiteNav() {
  const pathname = usePathname();
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(Boolean(getToken()));
  }, [pathname]);

  return (
    <nav className="flex items-center gap-1" aria-label="Main navigation">
      <div className="hidden items-center gap-1 md:flex">
        {LINKS.map((link) => {
          const isActive =
            link.href === "/" ? pathname === "/" : pathname.startsWith(link.href);
          return (
            <a
              key={link.href}
              href={link.href}
              className={cn(
                "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              )}
            >
              {link.label}
            </a>
          );
        })}
      </div>
      {authed ? (
        <button
          onClick={() => {
            setToken(null);
            setAuthed(false);
            window.location.href = "/login";
          }}
          className="rounded-md px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        >
          Sign out
        </button>
      ) : (
        <a
          href="/login"
          className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Sign in
        </a>
      )}
    </nav>
  );
}
