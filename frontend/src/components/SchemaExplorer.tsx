"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import type { TableSchema } from "./SqlQueryBlock";

type Props = {
  schema: Record<string, TableSchema> | null;
};

const TABLE_ORDER = ["listings", "reviews", "neighbourhoods"];
const DEFAULT_VISIBLE_COLS = 15;

const TABLE_ICONS: Record<string, ReactNode> = {
  listings: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  reviews: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  neighbourhoods: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
      <circle cx="12" cy="10" r="3" />
    </svg>
  ),
};

function TableCard({
  name,
  info,
}: {
  name: string;
  info: TableSchema;
}) {
  const [expanded, setExpanded] = useState(name === "listings");
  const [showAll, setShowAll] = useState(false);

  const colCount = info.columns.length;
  const needsTruncation = colCount > DEFAULT_VISIBLE_COLS;
  const visibleCols =
    showAll || !needsTruncation
      ? info.columns
      : info.columns.slice(0, DEFAULT_VISIBLE_COLS);

  return (
    <div className="schema-card">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[var(--color-surface-alt)]/50 transition-colors rounded-xl"
      >
        <div className="text-[var(--color-coral)] shrink-0">
          {TABLE_ICONS[name] ?? TABLE_ICONS.listings}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-sm text-[var(--color-navy)]">
              {name}
            </span>
            <span className="text-[0.65rem] px-1.5 py-0.5 rounded-full bg-[var(--color-teal)]/10 text-[var(--color-teal)] font-medium">
              {info.row_count.toLocaleString()} rows
            </span>
            <span className="text-[0.65rem] px-1.5 py-0.5 rounded-full bg-[var(--color-coral)]/10 text-[var(--color-coral)] font-medium">
              {colCount} cols
            </span>
          </div>
          <p className="text-xs text-[var(--color-gray-warm)] mt-0.5 truncate">
            {info.description}
          </p>
          <p className="text-[0.68rem] text-[var(--color-coral)] mt-1 font-medium">
            {expanded ? "Hide columns" : "Click to view columns"}
          </p>
        </div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`shrink-0 text-[var(--color-gray-warm)] transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {expanded && (
        <div className="schema-card-body px-4 pb-3">
          <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 mt-1">
            {visibleCols.map((col) => (
              <div
                key={col.name}
                className="flex items-center gap-1.5 text-[0.72rem] py-0.5"
              >
                <span className="text-[var(--color-navy)] font-medium truncate">
                  {col.name}
                </span>
                <span className="text-[var(--color-gray-warm)] opacity-70 text-[0.65rem] shrink-0">
                  {col.type}
                </span>
              </div>
            ))}
          </div>
          {needsTruncation && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowAll(!showAll);
              }}
              className="mt-2 text-xs text-[var(--color-coral)] hover:underline"
            >
              {showAll
                ? "Show fewer columns"
                : `Show all ${colCount} columns`}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function SchemaExplorer({ schema }: Props) {
  if (!schema) {
    return (
      <div>
        <h3 className="text-xs font-semibold text-[var(--color-navy)] mb-2 uppercase tracking-wider">
          Available Tables
        </h3>
        <div className="space-y-1.5">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-14 rounded-xl bg-white border border-[var(--color-border)] animate-pulse"
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-xs font-semibold text-[var(--color-navy)] mb-2 uppercase tracking-wider">
        Available Tables
      </h3>
      <p className="text-[0.75rem] text-[var(--color-gray-warm)] mb-3 leading-relaxed">
        Inspect the live schema for each dataset table. The main listings table opens by default.
      </p>
      <div className="space-y-1.5">
        {TABLE_ORDER.filter((t) => schema[t]).map((t) => (
          <TableCard key={t} name={t} info={schema[t]} />
        ))}
      </div>
    </div>
  );
}
