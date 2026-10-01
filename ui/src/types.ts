/** Shapes of the ENGRAMM app server's JSON API (engramm/app/server.py). */

export type ReplyKind =
  | "answer"
  | "unknown"
  | "learned"
  | "known"
  | "forgot"
  | "nothing"
  | "smalltalk"
  | "empathy"
  | "about"
  | "tool"
  | "memory"
  | "safety"
  | "writing";

export interface SourceView {
  kind: string;
  title: string;
  url: string | null;
  /** Atlas sources (shelf, feed, web): the date of the text. */
  as_of?: string | null;
  /** feed id or host of a web page */
  site?: string | null;
}

export interface Alternative {
  text: string | null;
  source: SourceView | null;
}

export interface Reply {
  kind: ReplyKind;
  text: string;
  answer: string | null;
  guess: string | null;
  evidence: string | null;
  source: SourceView | null;
  confidence: number;
  via: string;
  resolved: string | null;
  alternatives: Alternative[];
  seconds: number;
}

/** What the page stores for a failed request instead of a reply. */
export interface ErrorReply {
  error: string;
}

export type StoredReply = Reply | ErrorReply;

export interface Health {
  ready: boolean;
  error: string | null;
  mode: "full" | "quick" | null;
  sentences: number | null;
}

export interface MemoryItem {
  source: string;
  preview: string;
  tokens: number;
}

export type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; reply: StoredReply };

export interface Conversation {
  id: string;
  title: string;
  updated: number;
  messages: Message[];
}

export function isError(r: StoredReply): r is ErrorReply {
  return (r as ErrorReply).error !== undefined;
}

/** One network channel's settings (engramm/web/egress.py DEFAULT_SETTINGS). */
export interface ChannelSettings {
  enabled: boolean;
  tor?: boolean;
  feeds?: string[];
}

export type ChannelName = "shelf" | "feeds" | "messenger";

export interface FeedInfo {
  id: string;
  title: string;
  lang: string;
  selected: boolean;
}

export interface FeedState {
  last: number;
  ok: boolean;
  error: string;
}

/** One line of the network log: what was fetched, never why. */
export interface NetworkLogEntry {
  ts: string;
  channel: string;
  host: string;
  what: string;
  bytes: number;
  status: number;
  via: string;
  ok: boolean;
  error?: string;
}

export interface ShelfInfo {
  docs: number;
  date: string;
  buckets: number;
}

export type NetworkStatus =
  | { available: false }
  | {
      available: true;
      backend: string | null;
      channels: Record<ChannelName, ChannelSettings>;
      tor: string;
      feeds: FeedInfo[];
      feed_items: number;
      feed_state: Record<string, FeedState>;
      shelf: ShelfInfo | null;
      wayfinder: boolean;
      log: NetworkLogEntry[];
    };

export interface ChannelChange {
  channel: ChannelName;
  enabled?: boolean;
  tor?: boolean;
  feeds?: string[];
}
