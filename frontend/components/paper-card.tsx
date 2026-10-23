import type { Paper } from "@/lib/api";

export function PaperCard({ paper }: { paper: Paper }) {
  return (
    <article className="flex flex-col gap-3 rounded-lg border border-black/10 p-5 dark:border-white/15">
      <header className="flex flex-col gap-1">
        <h2 className="text-lg font-semibold leading-snug">{paper.title}</h2>
        <p className="text-sm text-black/60 dark:text-white/60">
          {paper.authors.length > 0 ? paper.authors.join(", ") : "Unknown authors"}
          {" · "}
          {paper.year || "Year unknown"}
        </p>
      </header>
      <p className="text-sm leading-relaxed">{paper.summary}</p>
      <a
        href={paper.url}
        target="_blank"
        rel="noopener noreferrer"
        className="self-start text-sm font-medium underline underline-offset-4"
      >
        View paper
      </a>
    </article>
  );
}
