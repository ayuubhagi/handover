// Handover mark: two overlapping rings, one passing into the other.
export function Logo({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--ink)" />
      <circle cx="12.5" cy="16" r="5.5" fill="none" stroke="var(--bg)" strokeWidth="2.5" />
      <circle cx="19.5" cy="16" r="5.5" fill="var(--accent)" />
    </svg>
  );
}
