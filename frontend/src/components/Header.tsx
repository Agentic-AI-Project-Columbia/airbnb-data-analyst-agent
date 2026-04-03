"use client";

export default function Header() {
  return (
    <header className="border-b border-[var(--color-border)] bg-white/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-3">
        <div className="w-9 h-9 gradient-coral rounded-lg flex items-center justify-center shadow-sm">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <path d="M7 16l4-8 4 4 4-10" />
          </svg>
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-tight text-[var(--color-navy)]">
            Airbnb Data Analyst
          </h1>
          <p className="text-xs text-[var(--color-gray-warm)]">
            Multi-agent analysis of NYC listings, pricing &amp; reviews
          </p>
        </div>
        <div className="ml-auto flex items-center gap-1.5 text-xs text-[var(--color-teal)] font-medium bg-[var(--color-teal)]/10 px-2.5 py-1 rounded-full">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)] animate-pulse" />
          3 Agents
        </div>
      </div>
    </header>
  );
}
