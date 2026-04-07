"use client";

import { useState } from "react";

type Props = {
  rowCount?: number;
  columns?: string[];
  preview?: Record<string, unknown>[];
};

export default function QueryResultSummary({ rowCount, columns, preview }: Props) {
  const [showPreview, setShowPreview] = useState(false);

  if (rowCount === undefined && !columns?.length) return null;

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2 flex-wrap">
        {rowCount !== undefined && columns && (
          <span className="result-badge">
            {rowCount.toLocaleString()} rows x {columns.length} columns
          </span>
        )}
        {rowCount !== undefined && !columns && (
          <span className="result-badge">
            {rowCount.toLocaleString()} rows
          </span>
        )}
      </div>

      {columns && columns.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap mt-1.5">
          {columns.map((col) => (
            <span
              key={col}
              className="inline-block text-[0.68rem] px-1.5 py-0.5 rounded bg-[var(--color-surface-alt)] text-[var(--color-navy)] border border-[var(--color-border)]"
            >
              {col}
            </span>
          ))}
        </div>
      )}

      {preview && preview.length > 0 && preview[0] && typeof preview[0] === "object" && (
        <div className="mt-1.5">
          <button
            onClick={() => setShowPreview(!showPreview)}
            className="text-[0.72rem] text-[var(--color-teal)] hover:text-[var(--color-teal-dark)] font-medium cursor-pointer"
          >
            {showPreview ? "Hide preview" : "Preview data"}
          </button>
          {showPreview && (
            <div className="mt-1 overflow-x-auto">
              <table className="text-[0.72rem] border-collapse w-full">
                <thead>
                  <tr>
                    {Object.keys(preview[0]).map((key) => (
                      <th
                        key={key}
                        className="text-left px-2 py-1 border border-[var(--color-border)] bg-[var(--color-surface-alt)] font-semibold text-[var(--color-navy)]"
                      >
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.map((row, i) => (
                    <tr key={i}>
                      {Object.values(row).map((val, j) => (
                        <td
                          key={j}
                          className="px-2 py-1 border border-[var(--color-border)] text-[var(--color-navy)] truncate max-w-[200px]"
                        >
                          {String(val ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
