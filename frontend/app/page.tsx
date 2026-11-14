import Link from "next/link";

const VIEWS = [
  { href: "/expert", title: "Expert", body: "Dana runs her exit interview. The agent asks about gaps and contradictions, and she decides who inherits each memory, corrects it, or forgets it." },
  { href: "/successor", title: "Successor", body: "Sam asks questions and hears Dana's own recorded answers. The runbook updates as Dana governs her memories." },
  { href: "/compare", title: "Memory on vs off", body: "The same question answered with and without Dana's memories." },
  { href: "/audit", title: "Audit", body: "Every read and governance action: who, what, allowed or blocked, and why." },
];

export default function Home() {
  return (
    <div>
      <div className="mb-10 max-w-2xl">
        <h1 className="font-serif text-4xl tracking-tight">Knowledge that stays when people leave.</h1>
        <p className="mt-3 text-lg text-muted">
          Handover interviews a departing expert and turns their answers into memory they govern: who inherits it, how long it lives, and when it is corrected or forgotten.
        </p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {VIEWS.map((v) => (
          <Link key={v.href} href={v.href} className="group rounded-xl border border-line bg-surface p-5 transition-colors hover:border-accent/40">
            <h2 className="font-serif text-xl">{v.title}</h2>
            <p className="mt-1.5 text-sm text-muted">{v.body}</p>
            <span className="mt-3 inline-block text-sm font-medium text-accent group-hover:underline">Open</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
