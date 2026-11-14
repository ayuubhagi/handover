"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import { CoffeeSticker, FoldedPaperSticker, KuroLaptopSticker, PipThinkingSticker } from "stick-it-up";
import { USE_MOCKS } from "../lib/config";
import { resetMock } from "../lib/mock";
import { IconMenu, IconMoon, IconPlus, IconSun, IconX } from "./icons";
import { Logo } from "./Logo";
import { chats, useChats, useTheme, setTheme, type Conversation } from "./store";

function group(list: Conversation[]) {
  const day = 86_400_000;
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const out: { label: string; items: Conversation[] }[] = [
    { label: "Today", items: [] },
    { label: "Yesterday", items: [] },
    { label: "Earlier", items: [] },
  ];
  for (const c of [...list].sort((a, b) => b.updatedAt - a.updatedAt)) {
    out[c.updatedAt >= today ? 0 : c.updatedAt >= today - day ? 1 : 2].items.push(c);
  }
  return out.filter((g) => g.items.length);
}

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

  const navItem = (href: string, label: string, sticker: React.ReactNode) => (
    <Link
      href={href}
      onClick={() => setOpen(false)}
      className={`flex items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm transition ${path === href ? "bg-active text-ink" : "text-muted hover:bg-hover hover:text-ink"}`}
    >
      <span className="sticker-icon h-6 w-6">{sticker}</span>
      {label}
    </Link>
  );

  return (
    <>
      <button onClick={() => setOpen(true)} aria-label="Open menu" className="fixed left-3 top-3 z-30 rounded-lg p-2 text-muted hover:bg-hover md:hidden">
        <IconMenu className="h-5 w-5" />
      </button>
      {open && <div className="fixed inset-0 z-30 bg-black/40 md:hidden" onClick={() => setOpen(false)} />}
      <aside
        className={`fixed inset-y-0 left-0 z-40 flex h-dvh w-64 shrink-0 flex-col overflow-hidden border-r border-line bg-sidebar/75 backdrop-blur-xl transition-transform md:static md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="flex items-center justify-between px-4 pb-3 pt-4">
          <Link href="/" onClick={() => goChat(() => chats.newChat())} className="flex items-center gap-2.5 text-[15px] font-semibold tracking-tight">
            <Logo />
            Handover
          </Link>
          <button onClick={() => setOpen(false)} aria-label="Close menu" className="rounded-md p-1 text-muted hover:bg-hover md:hidden">
            <IconX />
          </button>
        </div>

        <div className="px-3">
          <button
            onClick={() => goChat(() => chats.newChat())}
            className="flex w-full items-center gap-2 rounded-lg border border-line bg-surface/70 px-2.5 py-2 text-sm font-medium transition hover:bg-hover"
          >
            <IconPlus />
            New chat
          </button>
        </div>

        <nav className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pt-4">
          {conversations.length === 0 && (
            <div className="flex flex-col items-center gap-2 pt-8 text-sm text-soft">
              <span className="sticker-icon h-10 w-10 opacity-80">
                <PipThinkingSticker size={40} />
              </span>
              No chats yet
            </div>
          )}
          {group(conversations).map((g) => (
            <div key={g.label} className="mb-3">
              <p className="px-2 pb-1 text-[11px] font-medium uppercase tracking-wider text-soft">{g.label}</p>
              <ul className="space-y-px">
                {g.items.map((c) => {
                  const on = activeId === c.id && path === "/";
                  return (
                    <li key={c.id} className="group relative">
                      <button
                        onClick={() => goChat(() => chats.open(c.id))}
                        title={c.title}
                        className={`flex w-full items-center gap-2 rounded-lg py-1.5 pl-2 pr-7 text-left text-sm transition ${on ? "bg-active text-ink" : "text-muted hover:bg-hover hover:text-ink"}`}
                      >
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${c.mode === "interview" ? "bg-accent" : "bg-[#5ed6ce]"}`} />
                        <span className="truncate">{c.title}</span>
                      </button>
                      <button
                        onClick={() => chats.remove(c.id)}
                        aria-label={`Delete ${c.title}`}
                        className="absolute right-1 top-1/2 hidden -translate-y-1/2 rounded p-1 text-soft hover:text-ink group-hover:block"
                      >
                        <IconX className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="space-y-px border-t border-line px-3 pt-2">
          {navItem("/knows", "Handed over", <FoldedPaperSticker size={24} />)}
          {navItem("/under-the-hood", "Under the hood", <KuroLaptopSticker size={24} />)}
        </div>

        <div className="flex items-center justify-between px-4 py-3">
          {USE_MOCKS ? (
            <span className="flex items-center gap-1.5 text-xs text-soft">
              <span className="h-1.5 w-1.5 rounded-full bg-warn" />
              Mock
              <button onClick={() => resetMock()} className="ml-1 hover:text-ink hover:underline">
                Reset
              </button>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-xs text-soft">
              <span className="sticker-icon h-4 w-4">
                <CoffeeSticker size={16} />
              </span>
              Live
            </span>
          )}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            aria-label={theme === "dark" ? "Light mode" : "Dark mode"}
            className="rounded-md p-1.5 text-muted transition hover:bg-hover hover:text-ink"
          >
            {theme === "dark" ? <IconSun /> : <IconMoon />}
          </button>
        </div>
      </aside>
    </>
  );
}
