import { useEffect, useRef, useState } from "react";
import { ArrowUp, Bot, Database, FileText, Loader2, Siren, User } from "lucide-react";
import TopBar from "@/components/layout/TopBar";
import { backendStatus } from "@/data/backend";
import { cn } from "@/lib/utils";

type Answer = { text: string; citations: string[]; row_ids: string[]; known: boolean; emergency: boolean };
type Message = { role: "user"; text: string } | { role: "assistant"; answer?: Answer; error?: boolean; pending?: boolean };
type Lang = "en" | "ur";

const SUGGESTIONS: Record<Lang, string[]> = {
  en: [
    "What's happening in Pakistan right now?",
    "Where will it rain in the next 3 days?",
    "Which food prices jumped this week?",
    "How many people died in Buner flash floods in August 2025?",
    "Flood warning for river Sutlej",
    "Buner rain forecast",
  ],
  ur: ["آج کی صورتحال کیا ہے؟", "اگلے تین دنوں میں بارش کہاں ہوگی؟", "دریائے چناب میں سیلاب کی وارننگ", "Buner rain forecast"],
};

// Through the tunnel published in status.json (works on the public Space); else the local dev proxy.
// Read at ask time: status.json is loaded after this module is imported.
const askUrl = () => (backendStatus?.insight_url ? `${backendStatus.insight_url}/api/ask` : "/insight/ask");

/** One answer line: header, quoted section with citation, table fact with row id, or plain text. */
function AnswerLine({ line }: { line: string }) {
  const tag = line.match(/\[([^\]]+)\]\s*$/);
  const body = tag ? line.slice(0, tag.index).trim() : line;
  if (!line.startsWith("- ")) return <p className="text-sm font-medium" dir="auto">{line}</p>;
  const text = body.slice(2);
  const quote = text.match(/^"(.*)"\s*\((.*)\)$/s);
  if (quote) {
    return (
      <div className="rounded-md border border-border bg-muted/30 p-2.5" dir="auto">
        <p className="text-sm leading-relaxed">“{quote[1]}”</p>
        <p className="mt-1.5 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
          <FileText className="h-3.5 w-3.5" />
          {quote[2]}
          {tag && <code className="rounded bg-muted px-1 py-[1px] text-[10px]">§ {tag[1]}</code>}
        </p>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-2 text-sm" dir="auto">
      <Database className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      <span className="leading-relaxed">
        {text.split(/(https?:\/\/\S+)/).map((part, i) =>
          /^https?:\/\//.test(part) ? (
            <a key={i} href={part} target="_blank" rel="noreferrer" className="underline underline-offset-2">
              open PDF
            </a>
          ) : (
            part
          ),
        )}
        {tag && <code className="ml-1.5 rounded bg-muted px-1 py-[1px] text-[10px] text-muted-foreground">row {tag[1]}</code>}
      </span>
    </div>
  );
}

function AssistantBubble({ m }: { m: Extract<Message, { role: "assistant" }> }) {
  if (m.pending) {
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" /> Searching documents and tables…
      </p>
    );
  }
  if (m.error || !m.answer) {
    return (
      <p className="text-sm text-muted-foreground">
        The Insight Agent could not be reached. It runs on the FloodLens backend machine and is published through a
        tunnel; try again in a minute.
      </p>
    );
  }
  const lines = m.answer.text.split("\n").filter(Boolean);
  const disclaimer = lines.pop();
  return (
    <div className="space-y-2">
      {lines.map((line, i) =>
        m.answer!.emergency && i === 0 ? (
          <p key={i} className="flex gap-2 rounded-md border border-red-500/40 bg-red-500/10 p-2 text-sm text-red-700 dark:text-red-300" dir="auto">
            <Siren className="mt-0.5 h-4 w-4 shrink-0" />
            {line}
          </p>
        ) : (
          <AnswerLine key={i} line={line} />
        ),
      )}
      <p className="pt-1 text-xs text-muted-foreground" dir="auto">
        {m.answer.citations.length} document sections · {m.answer.row_ids.length} table rows cited · {disclaimer}
      </p>
    </div>
  );
}

/** Insight Agent as a chat: quotes NDMA documents and inserts numbers from FloodLens tables. */
export default function Ask() {
  const [lang, setLang] = useState<Lang>("en");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const endRef = useRef<HTMLDivElement>(null);
  const busy = messages.some((m) => m.role === "assistant" && m.pending);

  async function ask(question: string, language: Lang = lang) {
    const q = question.trim();
    if (q.length < 2 || busy) return;
    setInput("");
    setMessages((ms) => [...ms, { role: "user", text: q }, { role: "assistant", pending: true }]);
    let reply: Message;
    try {
      const res = await fetch(`${askUrl()}?${new URLSearchParams({ q, lang: language })}`);
      if (!res.ok) throw new Error(String(res.status));
      reply = { role: "assistant", answer: (await res.json()) as Answer };
    } catch {
      reply = { role: "assistant", error: true };
    }
    setMessages((ms) => [...ms.slice(0, -1), reply]);
  }

  // ?q=...&lang=ur asks straight away (shareable links)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search || window.location.hash.split("?")[1] || "");
    const l0 = params.get("lang") === "ur" ? "ur" : "en";
    setLang(l0);
    const q0 = params.get("q");
    if (q0) ask(q0, l0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <div className="flex h-[100dvh] flex-col bg-background">
      <TopBar />
      <div className="flex items-center justify-between gap-3 border-b border-border bg-card/40 px-4 py-2">
        <div>
          <h1 className="text-base font-semibold">Ask FloodLens</h1>
          <p className="text-xs text-muted-foreground">
            Answers quote NDMA documents with section ids and take every number from FloodLens tables with row ids. It
            says “I don’t know” when nothing supports an answer. Not an official warning.
          </p>
        </div>
        <div className="flex shrink-0 gap-1" role="group" aria-label="Answer language">
          {(["en", "ur"] as const).map((l) => (
            <button
              key={l}
              type="button"
              onClick={() => setLang(l)}
              className={cn("rounded border border-border px-2 py-1 text-xs", l === lang ? "bg-accent" : "hover:bg-accent/60")}
            >
              {l === "en" ? "English" : "اردو"}
            </button>
          ))}
        </div>
      </div>

      <div className="fl-scroll min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[860px] space-y-4 px-4 py-5">
          {messages.length === 0 && (
            <div className="py-6 text-center">
              <Bot className="mx-auto h-8 w-8 text-muted-foreground" />
              <p className="mt-2 text-lg font-semibold">What would you like to know?</p>
              <p className="text-sm text-muted-foreground">Live rain risk, forecasts and food prices, and NDMA reports.</p>
              <div className="mx-auto mt-4 grid max-w-[640px] gap-2 sm:grid-cols-2">
                {SUGGESTIONS[lang].map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => ask(s)}
                    dir="auto"
                    className="rounded-lg border border-border bg-card px-3 py-2.5 text-left text-sm transition-colors hover:bg-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end gap-2">
                <p className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2 text-sm text-primary-foreground" dir="auto">
                  {m.text}
                </p>
                <User className="mt-1.5 h-4 w-4 shrink-0 text-muted-foreground" />
              </div>
            ) : (
              <div key={i} className="flex gap-2">
                <Bot className="mt-1.5 h-4 w-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-border bg-card px-3.5 py-3">
                  <AssistantBubble m={m} />
                </div>
              </div>
            ),
          )}
          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-border bg-card/60 px-4 py-3">
        {messages.length > 0 && (
          <div className="mx-auto mb-2 flex max-w-[860px] gap-1.5 overflow-x-auto">
            {SUGGESTIONS[lang].slice(0, 3).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => ask(s)}
                dir="auto"
                className="shrink-0 rounded-full border border-border px-2.5 py-1 text-xs text-muted-foreground hover:bg-accent"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            ask(input);
          }}
          className="mx-auto flex max-w-[860px] items-end gap-2 rounded-xl border border-border bg-background p-1.5 shadow-sm"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            dir="auto"
            placeholder={lang === "ur" ? "اپنا سوال لکھیں…" : "Ask about rain risk, forecasts, food prices or NDMA reports…"}
            className="min-w-0 flex-1 bg-transparent px-2 py-1.5 text-sm outline-none"
          />
          <button
            type="submit"
            disabled={busy || input.trim().length < 2}
            aria-label="Send"
            className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground disabled:opacity-40"
          >
            <ArrowUp className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
