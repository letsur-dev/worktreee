/**
 * Parse SSE stream from fetch Response.
 * Yields parsed JSON objects from `data: {...}` lines.
 */
export async function* parseSSE<T = Record<string, unknown>>(
  response: Response,
): AsyncGenerator<T> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() || "";

    for (const chunk of chunks) {
      const line = chunk.trim();
      if (line.startsWith("data: ")) {
        try {
          yield JSON.parse(line.slice(6)) as T;
        } catch {
          // skip malformed JSON
        }
      }
    }
  }
}
