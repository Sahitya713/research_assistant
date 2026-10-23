import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SearchError, searchPapers } from "@/lib/api";

const samplePayload = {
  topic: "graphs",
  from_date: "2022-10-23",
  to_date: "2026-10-23",
  papers: [
    {
      id: "https://openalex.org/W1",
      title: "A paper",
      authors: ["Ada Lovelace"],
      year: 2025,
      summary: "Key finding.",
      url: "https://doi.org/10.1/x",
    },
  ],
};

describe("searchPapers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests the search endpoint with the topic and returns the JSON body", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify(samplePayload), { status: 200 }));

    const result = await searchPapers("graphs");

    expect(result).toEqual(samplePayload);
    const requested = new URL(vi.mocked(fetch).mock.calls[0][0] as URL);
    expect(requested.pathname).toBe("/api/search");
    expect(requested.searchParams.get("topic")).toBe("graphs");
  });

  it("surfaces the backend's detail message on error responses", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(JSON.stringify({ detail: "No papers found" }), { status: 404 }),
    );

    await expect(searchPapers("graphs")).rejects.toThrow(new SearchError("No papers found"));
  });

  it("falls back to a status message when the error body is not JSON", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("boom", { status: 500 }));

    await expect(searchPapers("graphs")).rejects.toThrow("Search failed with status 500.");
  });

  it("reports an unreachable server as a SearchError", async () => {
    vi.mocked(fetch).mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(searchPapers("graphs")).rejects.toBeInstanceOf(SearchError);
  });
});
