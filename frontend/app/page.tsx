"use client";
import { useState } from "react";
import TagInput from "@/components/TagInput";
import OutputCard from "@/components/OutputCard";

// const N8N_API = "https://slegendz.app.n8n.cloud/webhook-test/scrape";
// const LOCAL_API = "http://localhost:5001/scrape";

const LOCAL_API = process.env.NEXT_PUBLIC_BACKEND_URL!;
const N8N_API   = process.env.NEXT_PUBLIC_N8N_API!;

export default function Home() {
  const [urls, setUrls] = useState<string[]>([]);
  const [fields, setFields] = useState<string[]>([]);
  const [apiMode, setApiMode] = useState<"local" | "n8n">("n8n");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<
    { url: string; label: string; data: unknown }[]
  >([]);

  const addUrl = (v: string) => {
    if (!v) return;
    if (!v.startsWith("http")) v = "https://" + v;
    if (!urls.includes(v)) setUrls((p) => [...p, v]);
  };

  const scrapeOne = async (url: string) => {
    const endpoint = apiMode === "local" ? LOCAL_API : N8N_API;
    const payload =
      apiMode === "local" ? { url, fields } : { parameters: { url, fields } };

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  };

  const handleScrape = async () => {
    if (!urls.length) return alert("Please add at least one URL.");
    if (!fields.length) return alert("Please add at least one field.");
    setLoading(true);
    setResults([]);

    const settled = await Promise.allSettled(urls.map(scrapeOne));
    setResults(
      settled.map((r, i) => ({
        url: urls[i],
        label: urls[i],
        data:
          r.status === "fulfilled"
            ? r.value
            : { error: (r as PromiseRejectedResult).reason?.message },
      })),
    );
    setLoading(false);
  };

  return (
    <>
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-1.5 border border-border rounded-full px-3 py-1 text-[11px] text-muted mb-4">
          <span className="w-1.5 h-1.5 rounded-full bg-green" />
          AI-Powered · n8n Workflow
        </div>
        <h1 className="text-[clamp(24px,4vw,38px)] font-semibold text-text">
          AI Web Scraper
        </h1>
        <p className="mt-3 text-muted text-[15px] max-w-[460px] mx-auto">
          Extract structured data from any website using natural language field
          definitions.
        </p>
      </div>

      {/* Main Card */}
      <div className="w-full max-w-[780px] bg-surface border border-border rounded-card p-6 mb-5">
        {" "}
        {/* URLs */}
        <Label icon="🌐" text="Target URLs" />
        <TagInput
          tags={urls}
          onAdd={addUrl}
          onRemove={(i) => setUrls((p) => p.filter((_, j) => j !== i))}
          placeholder="https://example.com — press Enter to add"
          type="url"
          tagColor="green"
        />
        <Helper text="Press Enter or Tab to add · Backspace to remove last" />
        {/* Fields */}
        <Label icon="🏷️" text="Fields to Extract" className="mt-5" />
        <TagInput
          tags={fields}
          onAdd={(v) => {
            if (v && !fields.includes(v)) setFields((p) => [...p, v]);
          }}
          onRemove={(i) => setFields((p) => p.filter((_, j) => j !== i))}
          placeholder="title, price, rating — press Enter to add"
          extraTriggers={[","]}
        />
        <Helper text="Press Enter, Tab or , to add a field" />
        {/* API Mode */}
        <div className="flex items-center justify-between mt-5">
          <Label icon="🔗" text="API Mode" />
          <div className="flex gap-1.5">
            {(["local", "n8n"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setApiMode(m)}
                className={`px-3 py-1 rounded-full text-[11.5px] font-semibold border transition-all
                  ${
                    apiMode === m
                      ? "bg-accent/30 border-accent/60 text-accent2"
                      : "bg-surface2 border-border text-muted hover:border-accent hover:text-accent2"
                  }`}
              >
                {m === "local" ? "Local API" : "n8n Cloud"}
              </button>
            ))}
          </div>
        </div>
        {/* Scrape Button */}
        <button
          onClick={handleScrape}
          disabled={loading}
          className="flex items-center justify-center gap-2.5 w-full mt-5 py-4 bg-gradient-to-r from-accent to-accent2 rounded-sm text-white font-semibold text-[15px] hover:opacity-90 active:translate-y-0 disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none transition-all"
        >
          {loading && (
            <span className="w-[18px] h-[18px] rounded-full border-[2.5px] border-white/30 border-t-white animate-spin-slow" />
          )}
          <span className={loading ? "opacity-60" : ""}>
            {loading ? "Scraping…" : "Scrape Now"}
          </span>
        </button>
      </div>

      <OutputCard results={results} />
    </>
  );
}

function Label({
  icon,
  text,
  extra,
  className = "",
}: {
  icon: string;
  text: string;
  extra?: string;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center gap-2 text-[11px] font-bold tracking-widest uppercase text-muted mb-2 ${className}`}
    >
      <span className="w-[18px] h-[18px] grid place-items-center bg-accent/20 rounded-[5px] text-[10px]">
        {icon}
      </span>
      {text}
      {extra && (
        <span className="normal-case tracking-normal font-normal text-[10px] text-muted">
          {extra}
        </span>
      )}
    </div>
  );
}

function Helper({ text }: { text: string }) {
  return <p className="text-[11.5px] text-muted mt-1.5">{text}</p>;
}
