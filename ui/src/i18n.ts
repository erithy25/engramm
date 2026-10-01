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
  network: string;
  netOn: string;
  netOff: string;
  netIntro: string;
  netUnavailable: string;
  netLoading: string;
  shelfTitle: string;
  shelfDesc: string;
  shelfInfo: (docs: string, date: string) => string;
  shelfMissing: string;
  shelfTor: string;
  feedsTitle: string;
  feedsDesc: string;
  feedsItems: (n: number) => string;
  refreshFeeds: string;
  refreshing: string;
  feedFailed: string;
  messengerTitle: string;
  messengerDesc: string;
  messengerTor: string;
  messengerDirect: string;
  torState: (state: string) => string;
  netLog: string;
  netLogEmpty: string;
  netLogHead: [string, string, string, string, string];
  channelNames: Record<"shelf" | "feeds" | "messenger", string>;
  via: Record<"shelf" | "feed" | "web", string>;
  asOf: string;
  news: string;
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
  aboutLimits:
    "Limits: English first (German basics), weaker at long creative writing. Offline unless you switch on internet " +
    "access — and even then your questions stay on this computer. When unsure, ENGRAMM says so.",
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
  network: "Internet access",
  netOn: "on",
  netOff: "off",
  netIntro:
    "ENGRAMM works offline. Each channel below can be switched on by itself. Your questions never leave this " +
    "computer: ENGRAMM fetches whole shelf buckets, news feeds on a schedule or single pages — and answers here. " +
    "Every fetch is listed in the network log.",
  netUnavailable: "Internet access is not available in this version.",
  netLoading: "loading …",
  shelfTitle: "Full Wikipedia articles (shelf)",
  shelfDesc:
    "When the local knowledge has no answer, ENGRAMM downloads the bucket that holds the article — hundreds of " +
    "unrelated articles — plus two random decoy buckets. The host only sees bucket numbers.",
  shelfInfo: (docs, date) => `${docs} articles, as of ${date}`,
  shelfMissing: "This knowledge pack has no shelf index yet.",
  shelfTor: "over Tor (the host does not see your IP address)",
  feedsTitle: "News feeds",
  feedsDesc:
    "Fetches the feeds you pick every few hours at random times, independent of your questions. " +
    "Then ask “What's the latest news?”",
  feedsItems: (n) => (n === 1 ? "1 headline stored" : `${n.toLocaleString("en")} headlines stored`),
  refreshFeeds: "Fetch now",
  refreshing: "fetching …",
  feedFailed: "failed",
  messengerTitle: "Messenger (web pages over Tor)",
  messengerDesc:
    "For questions nothing else answers: fetches the official website or the live Wikipedia article and reads " +
    "it on your computer. The site sees an anonymous visit to that page, never your question.",
  messengerTor: "over Tor (recommended)",
  messengerDirect: "Without Tor the website sees your IP address.",
  torState: (s) =>
    s === "ready"
      ? "Tor: connected"
      : s === "starting"
        ? "Tor: connecting … (up to a minute)"
        : s === "unavailable"
          ? "Tor is not part of this build."
          : s.startsWith("failed")
            ? `Tor: ${s}`
            : "Tor: not started",
  netLog: "Network log",
  netLogEmpty: "Nothing fetched yet.",
  netLogHead: ["Time", "Channel", "Host", "What", "Size"],
  channelNames: { shelf: "shelf", feeds: "feeds", messenger: "messenger" },
  via: { shelf: "via shelf", feed: "via news feed", web: "via messenger" },
  asOf: "as of ",
  news: "News · ",
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
  aboutLimits:
    "Grenzen: vor allem Englisch (Deutsch in Grundzügen), schwächer bei langen kreativen Texten. Offline, solange du " +
    "den Internetzugang nicht einschaltest – und selbst dann bleiben deine Fragen auf diesem Rechner. Bei " +
    "Unsicherheit sagt ENGRAMM das.",
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
  network: "Internetzugang",
  netOn: "an",
  netOff: "aus",
  netIntro:
    "ENGRAMM arbeitet offline. Jeder Kanal unten lässt sich einzeln einschalten. Deine Fragen verlassen nie " +
    "diesen Rechner: ENGRAMM lädt ganze Regal-Fächer, Nachrichten-Feeds nach Zeitplan oder einzelne Seiten – und " +
    "antwortet hier. Jeder Abruf steht im Netzprotokoll.",
  netUnavailable: "Internetzugang ist in dieser Version nicht verfügbar.",
  netLoading: "lädt …",
  shelfTitle: "Vollständige Wikipedia-Artikel (Regal)",
  shelfDesc:
    "Findet das lokale Wissen keine Antwort, lädt ENGRAMM das Fach mit dem Artikel – Hunderte voneinander " +
    "unabhängige Artikel – plus zwei zufällige Tarn-Fächer. Der Host sieht nur Fach-Nummern.",
  shelfInfo: (docs, date) => `${docs} Artikel, Stand ${date}`,
  shelfMissing: "Dieses Wissenspaket hat noch keinen Regal-Index.",
  shelfTor: "über Tor (der Host sieht deine IP-Adresse nicht)",
  feedsTitle: "Nachrichten-Feeds",
  feedsDesc:
    "Lädt die gewählten Feeds alle paar Stunden zu zufälligen Zeiten, unabhängig von deinen Fragen. " +
    "Dann frag „What's the latest news?“",
  feedsItems: (n) => (n === 1 ? "1 Schlagzeile gespeichert" : `${n.toLocaleString("de")} Schlagzeilen gespeichert`),
  refreshFeeds: "Jetzt abrufen",
  refreshing: "ruft ab …",
  feedFailed: "fehlgeschlagen",
  messengerTitle: "Bote (Webseiten über Tor)",
  messengerDesc:
    "Für Fragen, die sonst nichts beantwortet: lädt die offizielle Website oder den aktuellen Wikipedia-Artikel " +
    "und liest ihn auf deinem Rechner. Die Seite sieht einen anonymen Besuch dieser Seite, nie deine Frage.",
  messengerTor: "über Tor (empfohlen)",
  messengerDirect: "Ohne Tor sieht die Website deine IP-Adresse.",
  torState: (s) =>
    s === "ready"
      ? "Tor: verbunden"
      : s === "starting"
        ? "Tor: verbindet … (bis zu einer Minute)"
        : s === "unavailable"
          ? "Tor ist in dieser Version nicht enthalten."
          : s.startsWith("failed")
            ? `Tor: ${s}`
            : "Tor: nicht gestartet",
  netLog: "Netzprotokoll",
  netLogEmpty: "Noch nichts abgerufen.",
  netLogHead: ["Zeit", "Kanal", "Host", "Was", "Größe"],
  channelNames: { shelf: "Regal", feeds: "Feeds", messenger: "Bote" },
  via: { shelf: "über das Regal", feed: "über einen Feed", web: "über den Boten" },
  asOf: "Stand ",
  news: "Nachrichten · ",
};

export const TEXTS: Record<Lang, Texts> = { en, de };
export const isLang = (v: unknown): v is Lang => v === "en" || v === "de";
