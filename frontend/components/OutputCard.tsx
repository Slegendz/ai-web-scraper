"use client";
import { useState } from "react";
import { useCopyToClipboard } from "usehooks-ts";
import { formatData } from "./FormatUtils";

interface ResultItem {
  url: string;
  label: string;
  data: unknown;
}

export default function OutputCard({ results }: { results: ResultItem[] }) {
  const [activeTab, setActiveTab] = useState(0);
  const [, copy] = useCopyToClipboard();
  const [copied, setCopied] = useState(false);
  const [search, setSearch] = useState("");

  if (!results.length) return null;

  const current = results[activeTab];
  const rawText = formatData(current.data);
  const isError = !!(current.data as Record<string, unknown>)?.error;

  const handleCopy = () => {
    copy(rawText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(
      new Blob([rawText], { type: "application/json" }),
    );
    a.download = `${current.label.replace(/[^a-z0-9]/gi, "_")}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const renderHighlighted = () => {
    if (!search.trim()) return <span>{rawText}</span>;
    const regex = new RegExp(
      `(${search.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`,
      "gi",
    );
    return rawText.split(regex).map((part, i) =>
      regex.test(part) ? (
        <mark key={i} className="bg-accent/40 text-white rounded-sm px-0.5">
          {part}
        </mark>
      ) : (
        <span key={i}>{part}</span>
      ),
    );
  };
  
  return (
    <div className="w-full max-w-[780px] bg-surface border border-border rounded-card overflow-hidden">
      {" "}
      <div className="flex items-center justify-between px-4 pt-3 pb-2 border-b border-border">
        <span className="text-[11px] text-muted uppercase tracking-widest">
          Output
        </span>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Highlight in output…"
          className="bg-bg border border-border rounded-sm px-2.5 py-1 text-xs text-text placeholder:text-muted outline-none focus:border-dim transition-colors w-32"
        />
      </div>
      {/* Tabs — only show if multiple results */}
      {results.length > 1 && (
        <div className="flex overflow-x-auto gap-0.5 px-5">
          {results.map((r, i) => (
            <button
              key={i}
              onClick={() => {
                setActiveTab(i);
                setSearch("");
              }}
              title={r.url}
              className={`shrink-0 px-4 py-1.5 rounded-t-lg text-xs font-medium border border-b-0 transition-all max-w-[200px] truncate
                ${activeTab === i ? "bg-surface2 border-border text-accent2" : "border-transparent text-muted hover:text-text hover:bg-white/[0.04]"}`}
            >
              {i + 1}. {r.label}
            </button>
          ))}
        </div>
      )}
      {/* Code Panel */}
      <div className="bg-surface2 border-t border-border">
        <pre
          className={`font-mono text-[13px] leading-7 p-5 overflow-auto h-[460px] ${isError ? "text-red" : "text-[#c4c9e8]"}`}
        >
          {renderHighlighted()}
        </pre>

        <div className="flex justify-end gap-2 px-4 pb-3">
          <button
            onClick={handleCopy}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs border transition-all
              ${copied ? "border-green text-green" : "bg-surface border-border text-muted hover:border-accent hover:text-accent2"}`}
          >
            {copied ? "✅ Copied!" : "📋 Copy"}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs border bg-surface border-border text-muted hover:border-green hover:text-green transition-all"
          >
            ⬇️ Download JSON
          </button>
        </div>
      </div>
    </div>
  );
}
