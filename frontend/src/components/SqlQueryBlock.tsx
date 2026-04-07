"use client";

import { useState } from "react";

export type TableSchema = {
  description: string;
  columns: { name: string; type: string }[];
  row_count: number;
};

type Props = {
  sql: string;
  tables?: string[];
  schema: Record<string, TableSchema> | null;
};

function SchemaPanel({ tableName, info }: { tableName: string; info: TableSchema }) {
  if (!info) return null;
  return (
    <div className="schema-popover">
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-[0.82rem] text-[var(--color-navy)]">
          {tableName}
        </span>
        <span className="text-[0.7rem] text-[var(--color-gray-warm)] bg-[var(--color-surface-alt)] px-2 py-0.5 rounded-full">
          {(info.row_count ?? 0).toLocaleString()} rows
        </span>
      </div>
      {info.description && (
        <p className="text-[0.75rem] text-[var(--color-gray-warm)] mb-2 leading-snug">
          {info.description}
        </p>
      )}
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
        {info.columns.map((col) => (
          <div key={col.name} className="flex items-center gap-1.5 text-[0.72rem] py-0.5">
            <span className="text-[var(--color-navy)] font-medium truncate">{col.name}</span>
            <span className="text-[var(--color-gray-warm)] opacity-70 text-[0.65rem] shrink-0">{col.type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SqlQueryBlock({ sql, tables, schema }: Props) {
  const [expandedTable, setExpandedTable] = useState<string | null>(null);

  const knownTables = new Set(tables || []);

  // Split SQL into segments, wrapping table names in clickable buttons
  const segments: { text: string; isTable: boolean; tableName?: string }[] = [];
  if (knownTables.size > 0 && schema) {
    const tablePattern = new RegExp(
      `\\b(${Array.from(knownTables).join("|")})\\b`,
      "gi"
    );
    let lastIndex = 0;
    let match: RegExpExecArray | null;
    while ((match = tablePattern.exec(sql)) !== null) {
      if (match.index > lastIndex) {
        segments.push({ text: sql.slice(lastIndex, match.index), isTable: false });
      }
      segments.push({ text: match[0], isTable: true, tableName: match[0].toLowerCase() });
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < sql.length) {
      segments.push({ text: sql.slice(lastIndex), isTable: false });
    }
  } else {
    segments.push({ text: sql, isTable: false });
  }

  return (
    <div className="mt-1.5">
      <div className="text-[0.65rem] uppercase tracking-widest text-[#8a8a9a] mb-1 font-semibold">
        sql
      </div>
      <pre className="trace-code-block text-[0.78rem] leading-[1.6] rounded-lg p-3 overflow-x-auto">
        <code>
          {segments.map((seg, i) =>
            seg.isTable && seg.tableName && schema?.[seg.tableName] ? (
              <button
                key={i}
                onClick={() =>
                  setExpandedTable(
                    expandedTable === seg.tableName! ? null : seg.tableName!
                  )
                }
                className={`sql-table-name ${expandedTable === seg.tableName ? "sql-table-name-active" : ""}`}
              >
                {seg.text}
              </button>
            ) : (
              <span key={i}>{seg.text}</span>
            )
          )}
        </code>
      </pre>
      {expandedTable && schema?.[expandedTable] && (
        <SchemaPanel tableName={expandedTable} info={schema[expandedTable]} />
      )}
    </div>
  );
}
