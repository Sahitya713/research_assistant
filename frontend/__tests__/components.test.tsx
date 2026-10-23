import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { PaperCard } from "@/components/paper-card";
import { SearchForm } from "@/components/search-form";
import type { Paper } from "@/lib/api";

const paper: Paper = {
  id: "https://openalex.org/W1",
  title: "Scaling Laws for Graph Models",
  authors: ["Ada Lovelace", "Alan Turing"],
  year: 2025,
  summary: "Larger graph models generalise better.",
  url: "https://doi.org/10.1/graph",
};

describe("PaperCard", () => {
  it("shows title, authors, year, summary and a link to the paper", () => {
    render(<PaperCard paper={paper} />);

    expect(screen.getByRole("heading", { name: paper.title })).toBeInTheDocument();
    expect(screen.getByText("Ada Lovelace, Alan Turing · 2025")).toBeInTheDocument();
    expect(screen.getByText(paper.summary)).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "View paper" });
    expect(link).toHaveAttribute("href", paper.url);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("handles missing authors and year gracefully", () => {
    render(<PaperCard paper={{ ...paper, authors: [], year: 0 }} />);
    expect(screen.getByText("Unknown authors · Year unknown")).toBeInTheDocument();
  });
});

describe("SearchForm", () => {
  it("submits the trimmed topic", () => {
    const onSearch = vi.fn();
    render(<SearchForm onSearch={onSearch} disabled={false} />);

    fireEvent.change(screen.getByLabelText("Research topic"), { target: { value: "  graphs  " } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    expect(onSearch).toHaveBeenCalledWith("graphs");
  });

  it("does not submit a topic shorter than two characters", () => {
    const onSearch = vi.fn();
    render(<SearchForm onSearch={onSearch} disabled={false} />);

    fireEvent.change(screen.getByLabelText("Research topic"), { target: { value: "a" } });
    fireEvent.submit(screen.getByRole("button", { name: "Search" }).closest("form")!);

    expect(onSearch).not.toHaveBeenCalled();
  });

  it("disables the button and shows progress while searching", () => {
    render(<SearchForm onSearch={vi.fn()} disabled={true} />);
    expect(screen.getByRole("button", { name: "Searching…" })).toBeDisabled();
  });
});
