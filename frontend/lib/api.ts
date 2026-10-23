export type Paper = {
  id: string;
  title: string;
  authors: string[];
  year: number;
  summary: string;
  url: string;
};

export type SearchResponse = {
  topic: string;
  from_date: string;
  to_date: string;
  papers: Paper[];
};

export class SearchError extends Error {}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Fetch up to four significant papers for `topic` from the backend. */
export async function searchPapers(
  topic: string,
  signal?: AbortSignal,
): Promise<SearchResponse> {
  const url = new URL("/api/search", API_BASE_URL);
  url.searchParams.set("topic", topic);

  let response: Response;
  try {
    response = await fetch(url, { signal });
  } catch {
    throw new SearchError("Could not reach the research assistant server.");
  }

  if (!response.ok) {
    throw new SearchError(await readErrorDetail(response));
  }
  return (await response.json()) as SearchResponse;
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
  } catch {
    // Fall through to the generic message below.
  }
  return `Search failed with status ${response.status}.`;
}
