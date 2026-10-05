import type { ChannelChange, Health, MemoryItem, NetworkStatus, Reply, Learning } from "./types";

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
  /** What ENGRAMM learned on this computer (corrections, taught words, style) and the reset. */
  learning: () => call<Learning>("/api/learning"),
  resetLearning: () => call<Learning>("/api/learning/reset", {}),
  /** The network channels (all off until switched on), their state and the network log. */
  network: () => call<NetworkStatus>("/api/network"),
  setNetwork: (change: ChannelChange) => call<NetworkStatus>("/api/network", change),
  refreshFeeds: () => call<NetworkStatus>("/api/network/refresh", {}),
  /** Desktop app only: the server opens a source link in the system browser. */
  open: (url: string) => call<{ opened: string }>("/api/open", { url }),
};
