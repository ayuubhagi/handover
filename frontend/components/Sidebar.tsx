"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { USE_MOCKS } from "../lib/config";
import { resetMock } from "../lib/mock";
import { IconBook, IconGear, IconMenu, IconMoon, IconPlus, IconSun, IconX } from "./icons";
import { chats, setTheme, useChats, useTheme } from "./store";

export function Sidebar() {
  const theme = useTheme();
  const { conversations, activeId } = useChats();
  const path = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);

  const goChat = (fn: () => void) => {
    fn();
    setOpen(false);
    if (path !== "/") router.push("/");
  };

  const navItem = (href: string, label: string, icon: React.ReactNode) => (
    <Link
      href={href}
      onClick={() => setOpen(false)}
      className={`flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition ${path === href ? "bg-active text-ink" : "text-muted hover:bg-hover hover:text-ink"}`}
    >
      {icon}
      {label}
    </Link>
  );

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="Open menu"
        className="fixed left-3 top-3 z-30 rounded-lg p-2 text-muted hover:bg-hover md:hidden"
      >
        <IconMenu className="h-5 w-5" />
      </button>
      {open && <div className="fixed inset-0 z-30 bg-black/30 md:hidden" onClick={() => setOpen(false)} />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col border-r border-line bg-sidebar/70 backdrop-blur-xl transition-transform md:static md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex items-center justify-between px-4 pb-2 pt-4">
          <Link href="/" onClick={() => setOpen(false)} className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
            <span className="grid h-6 w-6 place-items-center rounded-md bg-accent font-serif text-sm text-on-accent">h</span>
            Handover
          </Link>
          <button onClick={() => setOpen(false)} aria-label="Close menu" className="rounded-md p-1 text-muted hover:bg-hover md:hidden">
            <IconX />
          </button>
        </div>

        <div className="px-3 pt-2">
          <button
            onClick={() => goChat(() => chats.newChat())}
            className="flex w-full items-center gap-2.5 rounded-lg border border-line bg-surface px-2.5 py-2 text-sm font-medium shadow-sm transition hover:bg-hover"
          >
            <IconPlus />
            New conversation
          </button>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto px-3 pt-4">
          <p className="px-2.5 pb-1 text-xs font-medium text-soft">Conversations</p>
          {conversations.length === 0 && <p className="px-2.5 py-1 text-sm text-soft">Nothing yet.</p>}
          <ul className="space-y-0.5">
            {conversations.map((c) => (
              <li key={c.id}>
                <button
                  onClick={() => goChat(() => chats.open(c.id))}
                  className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm transition ${activeId === c.id && path === "/" ? "bg-active text-ink" : "text-muted hover:bg-hover hover:text-ink"}`}
                >
                  <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${c.mode === "interview" ? "bg-accent" : "bg-[#78d6d2]"}`} />
                  <span className="truncate">{c.title}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="space-y-0.5 px-3 pt-2">
          {navItem("/knows", "Handed over", <IconBook />)}
          {navItem("/under-the-hood", "Under the hood", <IconGear />)}
        </div>

        <div className="mt-2 border-t border-line px-3 py-3">
          <div className="flex items-center justify-between px-1">
            {USE_MOCKS ? (
              <span className="flex items-center gap-1.5 text-xs text-soft">
                <span className="h-1.5 w-1.5 rounded-full bg-warn" />
                Mock data
                <button onClick={() => resetMock()} className="ml-1 underline-offset-2 hover:text-ink hover:underline">
                  Reset
                </button>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-xs text-soft">
                <span className="h-1.5 w-1.5 rounded-full bg-ok" />
                Live backend
              </span>
            )}
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
              className="rounded-md p-1.5 text-muted transition hover:bg-hover hover:text-ink"
            >
              {theme === "dark" ? <IconSun /> : <IconMoon />}
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
