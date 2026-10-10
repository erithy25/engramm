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

/** One result of a web search (engramm/web/search.py), shown under the reply. */
export interface WebLink {
  title: string;
  url: string;
  site: string;
  snippet: string;
  engine: string;
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
  /** web search results (only replies of the web search have them; older stored replies lack the field) */
  links?: WebLink[];
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
  /** the knowledge pack the server runs on (desktop app); also set when loading failed */
  pack?: { name: string; version: string; bytes: number } | null;
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

export type SearchEngine = "auto" | "bing" | "duckduckgo" | "brave";
export const SEARCH_ENGINES: readonly SearchEngine[] = ["auto", "bing", "duckduckgo", "brave"];

/** One network channel's settings (engramm/web/egress.py DEFAULT_SETTINGS; the API key never comes back). */
export interface ChannelSettings {
  enabled: boolean;
  feeds?: string[];
  engine?: SearchEngine;
  brave_key_set?: boolean;
}

export type ChannelName = "shelf" | "feeds" | "search";

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
      feeds: FeedInfo[];
      feed_items: number;
      feed_state: Record<string, FeedState>;
      shelf: ShelfInfo | null;
      log: NetworkLogEntry[];
    };

export interface ChannelChange {
  channel: ChannelName;
  enabled?: boolean;
  feeds?: string[];
  engine?: SearchEngine;
  /** a Brave Search API key; "" removes it */
  brave_key?: string;
}

/** What ENGRAMM learned locally (engramm/learn): counts, taught words and style wishes. */
export interface Learning {
  available: boolean;
  corrections?: number;
  words?: string[];
  style?: Record<string, string>;
  episodes?: number;
  signals?: number;
}
