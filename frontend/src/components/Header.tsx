"use client";

type HeaderProps = {
  answered?: boolean;
  onReset?: () => void;
};

export default function Header({ answered, onReset }: HeaderProps) {
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
        <div className="ml-auto flex items-center gap-3">
          {answered && onReset && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 text-xs font-medium gradient-coral text-white px-3 py-1.5 rounded-full hover:opacity-90 active:scale-95 transition-all duration-150"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1 4 1 10 7 10" />
                <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
              </svg>
              New Question
            </button>
          )}
          <div className="flex items-center gap-1.5 text-xs text-[var(--color-teal)] font-medium bg-[var(--color-teal)]/10 px-2.5 py-1 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)] animate-pulse" />
            4 Agents
          </div>
        </div>
      </div>
    </header>
  );
}
