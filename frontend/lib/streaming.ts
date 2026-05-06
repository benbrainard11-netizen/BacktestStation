/**
 * NDJSON streaming consumer for FastAPI endpoints that respond with
 * application/x-ndjson — one JSON object per line, real-time as the
 * server writes them.
 *
 * Usage:
 *   for await (const event of streamNdjson<MyEvent>(url, body)) {
 *     // event is a parsed JSON object
 *   }
 *
 * Uses fetch + ReadableStream + TextDecoder. Buffers partial lines
 * across chunks. Throws on non-2xx (caller should catch + render).
 *
 * Used by AgentChatPanel against POST /api/strategies/{id}/chat-stream.
 */

export async function* streamNdjson<T>(
  url: string,
  body: unknown,
  init?: { signal?: AbortSignal },
): AsyncGenerator<T, void, unknown> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: init?.signal,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText || "Request failed"}`;
    try {
      const j = (await response.json()) as { detail?: string };
      if (j.detail) detail = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (!response.body) {
    throw new Error("response has no body to stream");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let nl: number;
      while ((nl = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, nl).trim();
        buffer = buffer.slice(nl + 1);
        if (!line) continue;
        try {
          yield JSON.parse(line) as T;
        } catch {
          // Skip malformed line (defensive). Stream continues.
        }
      }
    }
    // Flush any trailing buffered content (no trailing newline).
    const tail = (buffer + decoder.decode()).trim();
    if (tail) {
      try {
        yield JSON.parse(tail) as T;
      } catch {
        /* ignore */
      }
    }
  } finally {
    reader.releaseLock();
  }
}
