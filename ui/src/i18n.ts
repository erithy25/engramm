/** Interface texts. English first; German can be switched on. The conversation itself is English. */

export type Lang = "en" | "de";

interface Suggestion {
  title: string;
  sub: string;
}

export interface Texts {
  conversations: string;
  closeSidebar: string;
  openSidebar: string;
  newChat: string;
  history: string;
  memory: string;
  about: string;
  otherLanguage: string;
  darkMode: string;
  lightMode: string;
  pill: string;
  pillTitle: string;
  emptyTitle: string;
  emptySub: string;
  placeholder: string;
  message: string;
  send: string;
  hint: string;
  close: string;
  memorySub: string;
  aboutIntroBefore: string;
  aboutIntroBold: string;
  aboutIntroAfter: string;
  about1: string;
  about2: string;
  about3: string;
  about4: string;
  aboutLimits: string;
  today: string;
  earlier: string;
  untitled: string;
  deleteChat: string;
  loading: string;
  ready: string;
  loadError: string;
  offline: string;
  sentences: (millions: string) => string;
  quick: string;
  quickTitle: string;
  sure: string;
  sureTitle: string;
  unsure: string;
  unsureTitle: string;
  learned: string;
  forgot: string;
  understoodAs: string;
  seconds: string;
  openSource: string;
  copy: string;
  copied: string;
  copyFailed: string;
  evidence: string;
  hideEvidence: string;
  tool: string;
  safety: string;
  memoryChip: string;
  noMemory: string;
  forget: string;
  connectionLost: string;
  wikipedia: string;
  web: string;
  toldMe: string;
  writing: string;
  suggestions: Suggestion[];
}

const en: Texts = {
  conversations: "Conversations",
  closeSidebar: "Close sidebar",
  openSidebar: "Open sidebar",
  newChat: "New chat",
  history: "History",
  memory: "What ENGRAMM knows",
  about: "About ENGRAMM",
  otherLanguage: "Deutsch",
  darkMode: "Dark mode",
  lightMode: "Light mode",
  pill: "· no neural network",
  pillTitle: "Answers by counting, rules and hypervectors — no neural network",
  emptyTitle: "How can I help?",
  emptySub: "Ask me anything, tell me about yourself, or just chat. I show where every fact comes from.",
  placeholder: "Message ENGRAMM …",
  message: "Message",
  send: "Send",
  hint: "ENGRAMM works without a neural network and shows its sources — it can still be wrong. Check the source.",
  close: "Close",
  memorySub: "What you told ENGRAMM. “Forget” deletes it for real — not just hidden.",
  aboutIntroBefore: "ENGRAMM is a chat assistant that works ",
  aboutIntroBold: "without a neural network",
  aboutIntroAfter: ": counting, rules and hypervectors.",
  about1: "Facts come with their source — nothing is invented on purpose.",
  about2: "Remembers what you tell it (“My sister is called Anna”) — and truly forgets on request (“Forget my sister”).",
  about3: "Small talk, jokes, explanations (“Tell me about volcanoes”), e-mails and letters, calculations.",
  about4: "Runs entirely on your computer. Same question, same answer.",
  aboutLimits: "Limits: English only for now, no internet, weaker at long creative writing. When unsure, ENGRAMM says so.",
  today: "Today",
  earlier: "Earlier",
  untitled: "New chat",
  deleteChat: "Delete chat",
  loading: "loading its knowledge … (about a minute)",
  ready: "ready",
  loadError: "error while loading",
  offline: "no connection",
  sentences: (n) => ` · ${n} million sentences read`,
  quick: " · quick mode",
  quickTitle: "Quick mode: small sentence index. Full version: bash scripts/setup_mac.sh --full",
  sure: "confident",
  sureTitle: "Confidence above the threshold",
  unsure: "not sure",
  unsureTitle: "Best guess below the threshold",
  learned: "remembered",
  forgot: "forgotten",
  understoodAs: "understood as: ",
  seconds: "response time",
  openSource: "Open source",
  copy: "Copy",
  copied: "Copied",
  copyFailed: "Not possible",
  evidence: "Evidence",
  hideEvidence: "Hide evidence",
  tool: "calculated",
  safety: "help",
  memoryChip: "memory",
  noMemory: "Nothing yet. Tell ENGRAMM something, e.g. “My name is Alex.”",
  forget: "Forget",
  connectionLost: "No connection to ENGRAMM.",
  wikipedia: "Wikipedia · ",
  web: "Web · ",
  toldMe: "you told me",
  writing: "draft",
  suggestions: [
    { title: "Hi! My name is Alex.", sub: "Say hello — ENGRAMM remembers you" },
    { title: "Tell me about black holes", sub: "An explanation with its source" },
    { title: "Who wrote Pride and Prejudice?", sub: "A fact with evidence" },
    { title: "Write an email to my boss asking for a day off tomorrow", sub: "A draft you can change" },
  ],
};

const de: Texts = {
  ...en,
  conversations: "Unterhaltungen",
  closeSidebar: "Seitenleiste schließen",
  openSidebar: "Seitenleiste öffnen",
  newChat: "Neuer Chat",
  history: "Verlauf",
  memory: "Was ENGRAMM weiß",
  about: "Über ENGRAMM",
  otherLanguage: "English",
  darkMode: "Dunkles Design",
  lightMode: "Helles Design",
  pill: "· ohne neuronales Netz",
  pillTitle: "Antworten nur durch Zählen, Regeln und Hypervektoren – ohne neuronales Netz",
  emptyTitle: "Wie kann ich helfen?",
  emptySub: "Frag etwas, erzähl von dir oder plaudere einfach – auf Englisch. Zu jedem Fakt gibt es die Quelle.",
  placeholder: "Nachricht an ENGRAMM (auf Englisch) …",
  message: "Nachricht",
  send: "Senden",
  hint: "ENGRAMM arbeitet ohne neuronales Netz und zeigt seine Quellen – und kann sich trotzdem irren. Prüfe die Quelle.",
  close: "Schließen",
  memorySub: "Was du ENGRAMM erzählt hast. „Vergessen“ löscht es wirklich – nicht nur versteckt.",
  aboutIntroBefore: "ENGRAMM ist ein Chat, der ",
  aboutIntroBold: "ohne neuronales Netz",
  aboutIntroAfter: " arbeitet: nur Zählen, Regeln und Hypervektoren.",
  about1: "Fakten mit Quelle – nichts wird absichtlich erfunden.",
  about2: "Merkt sich, was du erzählst („My sister is called Anna“) – und vergisst es auf Befehl wirklich („Forget my sister“).",
  about3: "Smalltalk, Witze, Erklärungen („Tell me about volcanoes“), E-Mails und Briefe, Rechnen.",
  about4: "Läuft komplett auf deinem Rechner. Gleiche Frage – gleiche Antwort.",
  aboutLimits: "Grenzen: vorerst nur Englisch, kein Internet, schwächer bei langen kreativen Texten. Bei Unsicherheit sagt ENGRAMM das.",
  today: "Heute",
  earlier: "Früher",
  untitled: "Neuer Chat",
  deleteChat: "Chat löschen",
  loading: "lädt sein Wissen … (etwa eine Minute)",
  ready: "bereit",
  loadError: "Fehler beim Laden",
  offline: "keine Verbindung",
  sentences: (n) => ` · ${n} Mio. Sätze gelesen`,
  quick: " · Schnellmodus",
  quickTitle: "Schnellmodus: kleiner Satzindex. Volle Version: bash scripts/setup_mac.sh --full",
  sure: "sicher",
  sureTitle: "Konfidenz über der Schwelle",
  unsure: "unsicher",
  unsureTitle: "Beste Vermutung unter der Schwelle",
  learned: "gemerkt",
  forgot: "vergessen",
  understoodAs: "verstanden als: ",
  seconds: "Antwortzeit",
  openSource: "Quelle öffnen",
  copy: "Kopieren",
  copied: "Kopiert",
  copyFailed: "Nicht möglich",
  evidence: "Beleg",
  hideEvidence: "Beleg ausblenden",
  tool: "berechnet",
  safety: "Hilfe",
  memoryChip: "Gedächtnis",
  noMemory: "Noch nichts. Erzähl ENGRAMM etwas, z. B. „My name is Alex.“",
  forget: "Vergessen",
  connectionLost: "Keine Verbindung zu ENGRAMM.",
  toldMe: "von dir erzählt",
  writing: "Entwurf",
  suggestions: [
    { title: "Hi! My name is Alex.", sub: "Sag Hallo – ENGRAMM merkt sich dich" },
    { title: "Tell me about black holes", sub: "Eine Erklärung mit Quelle" },
    { title: "Who wrote Pride and Prejudice?", sub: "Ein Fakt mit Beleg" },
    { title: "Write an email to my boss asking for a day off tomorrow", sub: "Ein Entwurf zum Anpassen" },
  ],
};

export const TEXTS: Record<Lang, Texts> = { en, de };
export const isLang = (v: unknown): v is Lang => v === "en" || v === "de";
