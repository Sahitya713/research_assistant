import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Home from "@/app/page";

const payload = {
  topic: "graphs",
  from_date: "2022-10-23",
  to_date: "2026-10-23",
  papers: [1, 2, 3, 4].map((i) => ({
    id: `https://openalex.org/W${i}`,
    title: `Paper number ${i}`,
    authors: ["Ada Lovelace"],
    year: 2025,
    summary: `Summary ${i}.`,
    url: `https://doi.org/10.1/${i}`,
  })),
};

function submitTopic(topic: string) {
  fireEvent.change(screen.getByLabelText("Research topic"), { target: { value: topic } });
  fireEvent.click(screen.getByRole("button", { name: "Search" }));
}

describe("Home page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders four papers with the date window after a successful search", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    render(<Home />);

    submitTopic("graphs");

    expect(await screen.findByRole("heading", { name: "Paper number 1" })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(4);
    expect(screen.getByText(/2022-10-23 and 2026-10-23/)).toBeInTheDocument();
  });

  it("shows the backend error message when the search fails", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "No papers found for that topic" }), { status: 404 }),
    );
    render(<Home />);

    submitTopic("zzzz");

    expect(await screen.findByRole("alert")).toHaveTextContent("No papers found for that topic");
  });

  it("shows a loading message while the request is in flight", async () => {
    vi.mocked(fetch).mockReturnValue(new Promise(() => {}));
    render(<Home />);

    submitTopic("graphs");

    await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Searching…" })).toBeDisabled();
  });
});
