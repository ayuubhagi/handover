"use client";

import { useEffect } from "react";
import { useUserId } from "../lib/hooks";
import { loadStoredUser, setUserId } from "../lib/session";
import { PEOPLE, type UserId } from "../lib/types";
import { Menu } from "./Menu";

const DOT: Record<UserId, string> = {
  u_expert: "bg-accent",
  u_successor: "bg-[#78d6d2]",
  u_outsider: "bg-soft",
};

/** Top-right "viewing as" switch. Changes the X-User-Id the app sends. */
export function RoleMenu() {
  const user = useUserId();
  useEffect(() => loadStoredUser(), []);
  return (
    <div className="fixed right-3 top-3 z-30">
      <Menu
        label="Viewing as"
        value={user}
        onChange={(v) => setUserId(v as UserId)}
        options={PEOPLE.map((p) => ({
          value: p.id,
          label: p.name,
          hint: p.role,
          icon: <span className={`block h-2 w-2 translate-y-1 rounded-full ${DOT[p.id]}`} />,
        }))}
        trigger={(o) => (
          <span className="glass flex items-center gap-2 rounded-full border border-line py-1 pl-2.5 pr-1 text-[13px]">
            <span className={`h-2 w-2 rounded-full ${DOT[o.value as UserId]}`} />
            <span className="font-medium text-ink">{o.label}</span>
          </span>
        )}
      />
    </div>
  );
}
