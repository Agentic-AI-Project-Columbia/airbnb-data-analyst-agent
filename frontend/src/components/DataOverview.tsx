"use client";

import type { ReactNode } from "react";
import type { TableSchema } from "./SqlQueryBlock";

type Props = {
  schema: Record<string, TableSchema> | null;
};

const DEFAULT_COUNTS = {
  listings: 37257,
  reviews: 985674,
  neighbourhoods: 230,
  fields: 79,
};

export default function DataOverview({ schema }: Props) {
  const listingCount = schema?.listings?.row_count ?? DEFAULT_COUNTS.listings;
  const reviewCount = schema?.reviews?.row_count ?? DEFAULT_COUNTS.reviews;
  const neighbourhoodCount =
    schema?.neighbourhoods?.row_count ?? DEFAULT_COUNTS.neighbourhoods;
  const fieldCount =
    schema === null
      ? DEFAULT_COUNTS.fields
      : Object.values(schema).reduce(
          (total, table) => total + table.columns.length,
          0
        );

  const stats: { label: string; value: string; icon: ReactNode }[] = [
    {
      label: "Listings",
      value: listingCount.toLocaleString(),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>
      ),
    },
    {
      label: "Reviews",
      value: reviewCount.toLocaleString(),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
    },
    {
      label: "Neighbourhoods",
      value: neighbourhoodCount.toLocaleString(),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
          <circle cx="12" cy="10" r="3" />
        </svg>
      ),
    },
    {
      label: "Data Fields",
      value: fieldCount.toLocaleString(),
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="7" height="7" />
          <rect x="14" y="3" width="7" height="7" />
          <rect x="14" y="14" width="7" height="7" />
          <rect x="3" y="14" width="7" height="7" />
        </svg>
      ),
    },
  ];

  return (
    <div className="text-center mb-6 sm:mb-7">
      <div className="flex flex-col items-center justify-center gap-3 mb-3 sm:mb-4">
        <div className="w-11 h-11 gradient-coral rounded-2xl flex items-center justify-center shadow-md shrink-0">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 3v18h18" />
            <path d="M7 16l4-8 4 4 4-10" />
          </svg>
        </div>
        <div className="flex flex-col items-center gap-2">
          <h2 className="text-2xl sm:text-[2rem] font-bold tracking-tight text-[var(--color-navy)] leading-tight">
            NYC Airbnb Open Data
          </h2>
          <span className="text-[0.68rem] font-semibold px-2 py-1 rounded-full bg-[var(--color-teal)]/10 text-[var(--color-teal)] tracking-[0.14em] uppercase">
            2022 Dataset
          </span>
        </div>
      </div>

      <p className="text-[var(--color-gray-warm)] max-w-2xl mx-auto text-[0.92rem] sm:text-[0.98rem] leading-relaxed mb-4 sm:mb-5 px-2">
        Explore pricing, neighbourhood patterns, listing features, and guest review
        sentiment across all five NYC boroughs.
      </p>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 max-w-3xl mx-auto">
        {stats.map((s) => (
          <div
            key={s.label}
            className="flex flex-col items-center gap-1.5 px-3 py-3 rounded-xl bg-white border border-[var(--color-border)] shadow-sm"
          >
            <div className="text-[var(--color-teal)]">{s.icon}</div>
            <span className="text-xl sm:text-[1.35rem] font-bold text-[var(--color-navy)] leading-tight">
              {s.value}
            </span>
            <span className="text-[0.72rem] sm:text-[0.76rem] text-[var(--color-gray-warm)]">
              {s.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
