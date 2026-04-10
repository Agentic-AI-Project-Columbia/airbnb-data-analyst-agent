"use client";

import { useState, useRef, useEffect } from "react";

type ChatInputProps = {
  onSend: (message: string) => void;
  disabled: boolean;
};

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <div className="flex items-end gap-2 bg-white rounded-2xl border border-[var(--color-border)] p-2 shadow-sm focus-within:border-[var(--color-coral)] focus-within:shadow-md transition-all duration-200">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
          }
        }}
        placeholder="Ask a strategic Airbnb marketplace question..."
        disabled={disabled}
        rows={1}
        className="flex-1 resize-none bg-transparent px-3 py-2 text-[0.95rem]
                   placeholder:text-[var(--color-gray-warm)]/60 focus:outline-none
                   disabled:opacity-50"
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !input.trim()}
        className="gradient-coral text-white rounded-xl px-4 py-2 font-medium text-sm
                   hover:opacity-90 active:scale-95 transition-all duration-150
                   disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 2 11 13" />
          <path d="M22 2 15 22 11 13 2 9z" />
        </svg>
        Send
      </button>
    </div>
  );
}
