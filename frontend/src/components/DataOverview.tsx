"use client";

import type { ReactNode } from "react";
import type { TableSchema } from "./SqlQueryBlock";

type Props = {
  schema: Record<string, TableSchema> | null;
};

function formatCount(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M+`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K+`;
  return n.toLocaleString();
}

const STAT_ICONS: Record<string, ReactNode> = {
  Listings: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  Reviews: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  Neighbourhoods: (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  ),
  "Data Fields": (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="7" />
      <rect x="14" y="14" width="7" height="7" />
      <rect x="3" y="14" width="7" height="7" />
    </svg>
  ),
};

export default function DataOverview({ schema }: Props) {
  const stats = schema
    ? [
        { label: "Listings", value: formatCount(schema.listings?.row_count ?? 0) },
        { label: "Reviews", value: formatCount(schema.reviews?.row_count ?? 0) },
        { label: "Neighbourhoods", value: formatCount(schema.neighbourhoods?.row_count ?? 0) },
        {
          label: "Data Fields",
          value: Object.values(schema)
            .reduce((sum, t) => sum + (t.columns?.length ?? 0), 0)
            .toString(),
        },
      ]
    : null;

  return (
    <div className="text-center mb-5">
      <div className="flex items-center justify-center gap-3 mb-2">
        <div className="w-10 h-10 gradient-coral rounded-xl flex items-center justify-center shadow-md">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <path d="M7 16l4-8 4 4 4-10" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-[var(--color-navy)]">
          NYC Airbnb Open Data
          <span className="ml-2 text-[0.65rem] font-semibold px-1.5 py-0.5 rounded-full bg-[var(--color-teal)]/10 text-[var(--color-teal)] align-middle">
            2022
          </span>
        </h2>
      </div>

      <p className="text-[var(--color-gray-warm)] max-w-lg mx-auto text-[0.85rem] leading-relaxed mb-3">
        Explore pricing, neighbourhood patterns, listing features, and guest review
        sentiment across all five NYC boroughs.
      </p>

      <div className="grid grid-cols-4 gap-2 max-w-xl mx-auto">
        {stats
          ? stats.map((s) => (
              <div
                key={s.label}
                className="flex flex-col items-center gap-1 px-2 py-2 rounded-lg bg-white border border-[var(--color-border)] shadow-sm"
              >
                <div className="text-[var(--color-teal)]">
                  {STAT_ICONS[s.label]}
                </div>
                <span className="text-lg font-bold text-[var(--color-navy)] leading-tight">
                  {s.value}
                </span>
                <span className="text-[0.65rem] text-[var(--color-gray-warm)]">
                  {s.label}
                </span>
              </div>
            ))
          : Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="flex flex-col items-center gap-1 px-2 py-2 rounded-lg bg-white border border-[var(--color-border)] animate-pulse"
              >
                <div className="w-5 h-5 rounded bg-gray-200" />
                <div className="w-10 h-5 rounded bg-gray-200" />
                <div className="w-14 h-3 rounded bg-gray-100" />
              </div>
            ))}
      </div>
    </div>
  );
}
