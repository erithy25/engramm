import type { Health, MemoryItem, Reply } from "./types";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit =
    body === undefined
      ? {}
      : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const res = await fetch(path, init);
  let data: unknown = {};
  try {
    data = await res.json();
  } catch {
    data = {};
  }
  if (!res.ok) {
    const msg =
      typeof data === "object" && data !== null && "error" in data && typeof data.error === "string"
        ? data.error
        : `Error ${res.status}`;
    throw new ApiError(msg, res.status);
  }
  return data as T;
}

export const api = {
  health: () => call<Health>("/api/health"),
  chat: (conversation: string, message: string) => call<Reply>("/api/chat", { conversation, message }),
  memory: async () => (await call<{ items: MemoryItem[] }>("/api/memory")).items,
  forget: (source: string) => call<{ forgot: string }>("/api/memory/forget", { source }),
  /** Desktop app only: the server opens a source link in the system browser. */
  open: (url: string) => call<{ opened: string }>("/api/open", { url }),
};
