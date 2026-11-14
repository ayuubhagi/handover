// Handover mark: two rounded strokes passing one into the other, like a baton changing hands.
export function Logo({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--ink)" />
      <path d="M10 9v14" stroke="var(--bg)" strokeWidth="3" strokeLinecap="round" />
      <path d="M22 9v14" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" />
      <path d="M10 16h12" stroke="var(--accent)" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}
