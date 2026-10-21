import { useState } from "react";
import { MessageSquareText } from "lucide-react";
import PageHeader from "@/components/layout/PageHeader";
import TopBar from "@/components/layout/TopBar";
import Panel from "@/components/common/Panel";
import EmptyState from "@/components/common/EmptyState";

type Answer = { text: string; citations: string[]; row_ids: string[]; known: boolean; emergency: boolean };

const EXAMPLES = {
  en: ["How many people died in Buner flash floods in August 2025?", "Flood warning for river Sutlej",
    "Buner rain forecast", "Price of wheat flour in Lahore"],
  ur: ["دریائے چناب میں سیلاب کی وارننگ", "Buner rain forecast", "Price of wheat flour in Lahore"],
} as const;

/** Insight Agent: quotes official documents and inserts numbers from FloodLens tables. */
export default function Ask() {
  const [lang, setLang] = useState<"en" | "ur">("en");
  const [q, setQ] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");

  async function ask(question: string) {
    if (question.trim().length < 2) return;
    setQ(question);
    setState("loading");
    try {
      const res = await fetch(`/insight/ask?${new URLSearchParams({ q: question, lang })}`);
      if (!res.ok) throw new Error(String(res.status));
      setAnswer((await res.json()) as Answer);
      setState("idle");
    } catch {
      setState("error");
    }
  }

  return (
    <div className="min-h-[100dvh] bg-background">
      <div className="sticky top-0 z-30">
        <TopBar />
      </div>
      <div className="mx-auto w-full max-w-[900px] space-y-3 p-3 sm:p-4">
        <PageHeader
          title="Ask FloodLens"
          subtitle="Answers quote NDMA documents with section ids and take numbers from FloodLens tables with row ids. Not an official warning."
        />
        <Panel
          title="Question"
          action={
            <div className="flex gap-1" role="group" aria-label="Answer language">
              {(["en", "ur"] as const).map((l) => (
                <button
                  key={l}
                  type="button"
                  onClick={() => setLang(l)}
                  className={`rounded border border-border px-2 py-1 text-xs ${l === lang ? "bg-accent" : "hover:bg-accent/60"}`}
                >
                  {l === "en" ? "English" : "اردو"}
                </button>
              ))}
            </div>
          }
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              ask(q);
            }}
            className="flex gap-2"
          >
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              dir="auto"
              placeholder={lang === "ur" ? "اپنا سوال لکھیں" : "e.g. Deaths in Swat during monsoon 2025"}
              className="min-w-0 flex-1 rounded border border-border bg-background px-3 py-2 text-sm"
            />
            <button type="submit" className="rounded border border-border px-3 py-2 text-sm hover:bg-accent">
              Ask
            </button>
          </form>
          <div className="mt-2 flex flex-wrap gap-1">
            {EXAMPLES[lang].map((ex) => (
              <button
                key={ex}
                type="button"
                onClick={() => ask(ex)}
                dir="auto"
                className="rounded border border-border px-2 py-0.5 text-xs text-muted-foreground hover:bg-accent/60"
              >
                {ex}
              </button>
            ))}
          </div>
        </Panel>

        {state === "error" ? (
          <EmptyState
            icon={MessageSquareText}
            title="The Insight Agent is not running"
            description="Start it in backend/: .venv-insight/bin/uvicorn src.insight_api:app --port 8001"
          />
        ) : state === "loading" ? (
          <p className="text-sm text-muted-foreground">Searching documents…</p>
        ) : answer ? (
          <Panel
            title={answer.known ? "Answer" : "No reliable answer"}
            subtitle={`${answer.citations.length} document sections · ${answer.row_ids.length} table rows cited`}
          >
            <div dir="auto" className="space-y-1.5 whitespace-pre-wrap text-sm leading-relaxed">
              {answer.text.split("\n").map((line, i) => (
                <p key={i} className={line.startsWith("- ") ? "pl-3" : "font-medium"}>
                  {line}
                </p>
              ))}
            </div>
          </Panel>
        ) : null}
      </div>
    </div>
  );
}
