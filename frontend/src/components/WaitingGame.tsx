"use client";

import { useState, useEffect, useCallback } from "react";

const EMOJIS = ["🏠", "✈️", "🧳", "🌴", "🗽", "🏖️", "🌊", "⭐"];

type Card = {
  id: number;
  emoji: string;
  flipped: boolean;
  matched: boolean;
};

function shuffleArray<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function buildDeck(): Card[] {
  const pairs = shuffleArray([...EMOJIS, ...EMOJIS]);
  return pairs.map((emoji, i) => ({
    id: i,
    emoji,
    flipped: false,
    matched: false,
  }));
}

export default function WaitingGame() {
  const [cards, setCards] = useState<Card[]>(buildDeck);
  const [selected, setSelected] = useState<number[]>([]);
  const [pairsFound, setPairsFound] = useState(0);
  const [moves, setMoves] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const handleFlip = useCallback(
    (id: number) => {
      if (selected.length === 2) return;
      const card = cards[id];
      if (card.flipped || card.matched) return;

      const next = cards.map((c) =>
        c.id === id ? { ...c, flipped: true } : c
      );
      setCards(next);

      const newSelected = [...selected, id];
      setSelected(newSelected);

      if (newSelected.length === 2) {
        setMoves((m) => m + 1);
        const [a, b] = newSelected;
        if (next[a].emoji === next[b].emoji) {
          setTimeout(() => {
            setCards((prev) =>
              prev.map((c) =>
                c.id === a || c.id === b ? { ...c, matched: true } : c
              )
            );
            setPairsFound((p) => p + 1);
            setSelected([]);
          }, 400);
        } else {
          setTimeout(() => {
            setCards((prev) =>
              prev.map((c) =>
                c.id === a || c.id === b ? { ...c, flipped: false } : c
              )
            );
            setSelected([]);
          }, 700);
        }
      }
    },
    [cards, selected]
  );

  const resetGame = useCallback(() => {
    setCards(buildDeck());
    setSelected([]);
    setPairsFound(0);
    setMoves(0);
  }, []);

  const allMatched = pairsFound === EMOJIS.length;
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;

  return (
    <div className="waiting-game-enter flex flex-col items-center gap-4 py-6">
      <div className="flex items-center gap-2 text-sm text-[var(--color-gray-warm)]">
        <span className="thinking-dots flex gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" />
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" />
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" />
        </span>
        <span className="italic">
          Your agent is working&hellip;
          <span className="ml-1.5 tabular-nums font-medium text-[var(--color-teal)]">
            {minutes > 0 && `${minutes}m `}{seconds.toString().padStart(2, "0")}s
          </span>
        </span>
      </div>

      <p className="text-xs text-[var(--color-gray-warm)]/70">
        {allMatched
          ? "Nice work! Waiting for results..."
          : "Play while you wait — find all matching pairs!"}
      </p>

      <div className="grid grid-cols-4 gap-2.5 select-none">
        {cards.map((card) => (
          <button
            key={card.id}
            onClick={() => handleFlip(card.id)}
            aria-label={
              card.flipped || card.matched ? card.emoji : "Hidden card"
            }
            className={`memory-card ${card.flipped || card.matched ? "memory-card-flipped" : ""} ${card.matched ? "memory-card-matched" : ""}`}
          >
            <span className="memory-card-inner">
              <span className="memory-card-front" aria-hidden="true" />
              <span className="memory-card-back">
                <span className="text-2xl leading-none">{card.emoji}</span>
              </span>
            </span>
          </button>
        ))}
      </div>

      <div className="flex items-center gap-4 text-xs text-[var(--color-gray-warm)]">
        <span>
          Pairs:{" "}
          <span className="font-semibold text-[var(--color-teal)]">
            {pairsFound}/{EMOJIS.length}
          </span>
        </span>
        <span>
          Moves: <span className="font-semibold">{moves}</span>
        </span>
        {allMatched && (
          <button
            onClick={resetGame}
            className="text-[var(--color-coral)] font-semibold hover:underline"
          >
            Play again
          </button>
        )}
      </div>
    </div>
  );
}
