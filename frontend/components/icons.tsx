// Small stroke icons, 1.75px, currentColor.
type P = { className?: string };
const base = (d: React.ReactNode, { className = "h-4 w-4" }: P) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    {d}
  </svg>
);

export const IconPlus = (p: P) => base(<path d="M12 5v14M5 12h14" />, p);
export const IconMic = (p: P) => base(<><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></>, p);
export const IconMicOff = (p: P) => base(<><path d="M15 10V6a3 3 0 0 0-5.7-1.3M9 9v2a3 3 0 0 0 5 2.2M5 11a7 7 0 0 0 11.5 5.4M19 11a7 7 0 0 1-.6 2.8M12 18v3M3 3l18 18" /></>, p);
export const IconArrowUp = (p: P) => base(<path d="M12 19V5M6 11l6-6 6 6" />, p);
export const IconStop = (p: P) => base(<rect x="7" y="7" width="10" height="10" rx="2" />, p);
export const IconPhone = (p: P) => base(<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z" />, p);
export const IconPhoneOff = (p: P) => base(<><path d="M10.7 13.3a11 11 0 0 0 2.8 2.2L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 6.3 15.8M4.2 11A16 16 0 0 1 3 6a2 2 0 0 1 2-2h4l2 5-2.5 1.5" /><path d="M3 21 21 3" /></>, p);
export const IconPlay = (p: P) => base(<path d="M8 5v14l11-7z" />, p);
export const IconPause = (p: P) => base(<path d="M8 5v14M16 5v14" />, p);
export const IconSun = (p: P) => base(<><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></>, p);
export const IconMoon = (p: P) => base(<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5Z" />, p);
export const IconBook = (p: P) => base(<><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5Z" /><path d="M4 19a2 2 0 0 1 2-2h13" /></>, p);
export const IconGear = (p: P) => base(<><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z" /></>, p);
export const IconCheck = (p: P) => base(<path d="m5 12 5 5L20 7" />, p);
export const IconX = (p: P) => base(<path d="M6 6l12 12M18 6 6 18" />, p);
export const IconLock = (p: P) => base(<><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>, p);
export const IconChat = (p: P) => base(<path d="M4 5h16v11H8l-4 4V5Z" />, p);
export const IconMenu = (p: P) => base(<path d="M4 7h16M4 12h16M4 17h16" />, p);
