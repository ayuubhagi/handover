"use client";

import { useEffect, useId, useRef, useState } from "react";
import { IconCheck, IconChevron } from "./icons";

export interface MenuOption<T extends string> {
  value: T;
  label: string;
  hint?: string;
  icon?: React.ReactNode;
}

/** Small custom select: button + listbox popover, keyboard friendly. Opens up or down. */
export function Menu<T extends string>({
  value,
  options,
  onChange,
  label,
  placement = "bottom-end",
  trigger,
  className = "",
}: {
  value: T;
  options: MenuOption<T>[];
  onChange: (v: T) => void;
  label: string;
  placement?: "bottom-end" | "top-start";
  trigger?: (current: MenuOption<T>) => React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [focus, setFocus] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();
  const current = options.find((o) => o.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    list.current?.focus();
    return () => document.removeEventListener("pointerdown", onDown);
  }, [open]);

  const pick = (v: T) => {
    onChange(v);
    setOpen(false);
  };

  return (
    <div ref={root} className={`relative ${className}`}>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={id}
        aria-label={`${label}: ${current.label}`}
        onClick={() => {
          setFocus(Math.max(0, options.indexOf(current)));
          setOpen((o) => !o);
        }}
        className="flex items-center gap-2 rounded-full px-2.5 py-1.5 text-[13px] text-muted transition hover:bg-hover hover:text-ink"
      >
        {trigger ? trigger(current) : (
          <>
            {current.icon}
            <span className="font-medium text-ink">{current.label}</span>
          </>
        )}
        <IconChevron className={`h-3.5 w-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <ul
          ref={list}
          id={id}
          role="listbox"
          tabIndex={-1}
          aria-label={label}
          aria-activedescendant={`${id}-${focus}`}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setFocus((f) => (f + 1) % options.length);
            else if (e.key === "ArrowUp") setFocus((f) => (f - 1 + options.length) % options.length);
            else if (e.key === "Enter" || e.key === " ") pick(options[focus].value);
            else if (e.key === "Escape") setOpen(false);
            else return;
            e.preventDefault();
          }}
          className={`menu-pop absolute z-50 min-w-40 rounded-2xl border border-line bg-raised/95 p-1.5 shadow-[var(--shadow-pop)] backdrop-blur-xl outline-none ${placement === "bottom-end" ? "right-0 top-full mt-2 origin-top-right" : "bottom-full left-0 mb-2 origin-bottom-left"}`}
        >
          {options.map((o, i) => (
            <li
              key={o.value}
              id={`${id}-${i}`}
              role="option"
              aria-selected={o.value === value}
              onPointerEnter={() => setFocus(i)}
              onClick={() => pick(o.value)}
              className={`flex cursor-pointer items-start gap-2.5 rounded-xl px-2.5 py-2 ${focus === i ? "bg-hover" : ""}`}
            >
              {o.icon && <span className="mt-0.5 shrink-0">{o.icon}</span>}
              <span className="min-w-0 flex-1">
                <span className="block text-sm text-ink">{o.label}</span>
                {o.hint && <span className="block text-xs text-soft">{o.hint}</span>}
              </span>
              {o.value === value && <IconCheck className="mt-0.5 h-4 w-4 shrink-0 text-accent" />}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
