"use client";

import { useRef, useState } from "react";
import { PaperCard } from "@/components/paper-card";
import { SearchForm } from "@/components/search-form";
import { type SearchResponse, SearchError, searchPapers } from "@/lib/api";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; result: SearchResponse };

export default function Home() {
  const [state, setState] = useState<State>({ status: "idle" });
  const controllerRef = useRef<AbortController | null>(null);

  async function handleSearch(topic: string) {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;

    setState({ status: "loading" });
    try {
      const result = await searchPapers(topic, controller.signal);
      setState({ status: "success", result });
    } catch (error) {
      if (controller.signal.aborted) {
        return;
      }
      const message =
        error instanceof SearchError
          ? error.message
          : "Something went wrong. Please try again.";
      setState({ status: "error", message });
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-8 px-4 py-12">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Research Assistant</h1>
        <p className="text-black/60 dark:text-white/60">
          Enter a topic to see four significant papers from the last four years.
        </p>
      </header>

      <SearchForm onSearch={handleSearch} disabled={state.status === "loading"} />

      {state.status === "loading" && (
        <p role="status" className="text-black/60 dark:text-white/60">
          Finding and summarising papers. This can take up to a minute.
        </p>
      )}

      {state.status === "error" && (
        <p role="alert" className="text-red-600 dark:text-red-400">
          {state.message}
        </p>
      )}

      {state.status === "success" && (
        <section aria-label="Results" className="flex flex-col gap-6">
          <p className="text-sm text-black/60 dark:text-white/60">
            Papers published between {state.result.from_date} and{" "}
            {state.result.to_date} on &ldquo;{state.result.topic}&rdquo;.
          </p>
          {state.result.papers.map((paper) => (
            <PaperCard key={paper.id} paper={paper} />
          ))}
        </section>
      )}
    </main>
  );
}
