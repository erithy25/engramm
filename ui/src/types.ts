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
