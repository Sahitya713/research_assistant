"use client";

import { type FormEvent, useState } from "react";

type SearchFormProps = {
  onSearch: (topic: string) => void;
  disabled: boolean;
};

export function SearchForm({ onSearch, disabled }: SearchFormProps) {
  const [topic, setTopic] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleaned = topic.trim();
    if (cleaned.length < 2) {
      return;
    }
    onSearch(cleaned);
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full gap-2">
      <label htmlFor="topic" className="sr-only">
        Research topic
      </label>
      <input
        id="topic"
        name="topic"
        type="text"
        value={topic}
        onChange={(event) => setTopic(event.target.value)}
        placeholder="e.g. large language model evaluation"
        maxLength={200}
        required
        minLength={2}
        className="flex-1 rounded-md border border-black/20 bg-transparent px-3 py-2 text-base outline-none focus:border-black dark:border-white/25 dark:focus:border-white"
      />
      <button
        type="submit"
        disabled={disabled}
        className="rounded-md bg-black px-4 py-2 text-base font-medium text-white disabled:opacity-50 dark:bg-white dark:text-black"
      >
        {disabled ? "Searching…" : "Search"}
      </button>
    </form>
  );
}
