"use client";
import { useState, useRef, KeyboardEvent } from "react";

interface Props {
  tags: string[];
  onAdd: (v: string) => void;
  onRemove: (i: number) => void;
  placeholder: string;
  type?: string;
  extraTriggers?: string[];
  tagColor?: "purple" | "green";
}

export default function TagInput({
  tags,
  onAdd,
  onRemove,
  placeholder,
  type = "text",
  extraTriggers = [],
  tagColor = "purple",
}: Props) {
  const [val, setVal] = useState("");
  const ref = useRef<HTMLInputElement>(null);

  const commit = () => {
    const v = val.replace(/,/g, "").trim();
    if (v) {
      onAdd(v);
      setVal("");
    }
  };

  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (["Enter", "Tab", ...extraTriggers].includes(e.key)) {
      e.preventDefault();
      commit();
    }
    if (e.key === "Backspace" && !val && tags.length) onRemove(tags.length - 1);
  };

  const tagClass =
    tagColor === "green"
      ? "bg-green/20 border-green/40 text-green"
      : "bg-accent/25 border-accent/45 text-accent2";

  return (
    <div
      onClick={() => ref.current?.focus()}
      className="flex flex-wrap gap-2 items-center bg-bg border border-border rounded-sm px-3 py-2.5 min-h-[48px] cursor-text focus-within:border-dim transition-colors"
    >
      {tags.map((t, i) => (
        <span
          key={i}
          className={`inline-flex items-center gap-1.5 border rounded-full px-3 py-1 text-[12.5px] font-medium ${tagClass}`}
        >
          <span className="max-w-[260px] truncate" title={t}>
            {t}
          </span>
          <button
            onClick={() => onRemove(i)}
            className="w-4 h-4 rounded-full bg-white/10 text-muted text-[11px] hover:bg-red hover:text-white transition-colors grid place-items-center shrink-0"
          >
            ✕
          </button>
        </span>
      ))}

      <input
        ref={ref}
        type={type}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={onKey}
        onBlur={commit}
        placeholder={tags.length ? "" : placeholder}
        autoComplete="off"
        spellCheck={false}
        className="flex-1 min-w-[160px] bg-transparent outline-none text-sm text-text placeholder:text-muted"
      />
    </div>
  );
}
