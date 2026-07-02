import type { SseFrame } from "../types";

export async function readSseStream(
  stream: ReadableStream<Uint8Array> | null,
  onFrame: (frame: SseFrame) => void
): Promise<void> {
  if (!stream) {
    throw new Error("Response did not include a stream body");
  }

  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawFrame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const frame = parseFrame(rawFrame);
      if (frame) {
        onFrame(frame);
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function parseFrame(raw: string): SseFrame | null {
  if (!raw.trim() || raw.startsWith(":")) {
    return null;
  }

  let event = "message";
  let id: string | undefined;
  const dataLines: string[] = [];

  for (const line of raw.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("id:")) {
      id = line.slice("id:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    id,
    event,
    data: JSON.parse(dataLines.join("\n"))
  };
}
