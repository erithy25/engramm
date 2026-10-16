// First-run, start and pack page of the ENGRAMM desktop app (runs inside the app window only).
// With a pack installed it also lists every pack: download another (lite → standard), switch,
// delete one that is not in use. The chat page opens it with ?manage=1.
"use strict";

const tauri = window.__TAURI__;
const $ = (id) => document.getElementById(id);
const sections = ["error", "ready", "install", "progress"];
const params = new URLSearchParams(window.location.search);
const TITLES = { lite: "Lite", standard: "Standard" };

function show(...ids) {
  for (const s of sections) $(s).hidden = !ids.includes(s);
}

function gb(bytes) {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${Math.max(1, Math.round(bytes / 1e6))} MB`;
}

function packTitle(p) {
  return p.title || TITLES[p.name] || p.name;
}

function showError(message) {
  $("errorText").textContent = message;
  $("lead").textContent = "";
  show("error");
}

async function invoke(cmd, args) {
  if (!tauri) throw new Error("This page only works inside the ENGRAMM app.");
  return tauri.core.invoke(cmd, args);
}

function button(label, onClick, primary = false) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = label;
  if (primary) b.className = "primary";
  b.addEventListener("click", onClick);
  return b;
}

function badge(text) {
  const s = document.createElement("span");
  s.className = "badge";
  s.textContent = text;
  return s;
}

function row(title, desc, actions) {
  const r = document.createElement("div");
  r.className = "pack";
  const info = document.createElement("div");
  const t = document.createElement("b");
  t.textContent = title;
  const d = document.createElement("span");
  d.className = "small muted";
  d.textContent = desc;
  info.append(t, d);
  const a = document.createElement("div");
  a.className = "actions";
  a.append(...actions);
  r.append(info, a);
  return r;
}

// One row per pack: the catalog's (download, or switch to / delete the installed copy) and any
// other complete pack on this computer (for example a folder from a USB stick).
function renderPacks(st) {
  const box = $("catalog");
  box.textContent = "";
  const installed = st.installed || [];
  const has = st.pack !== null && st.pack !== undefined;
  $("noCatalog").hidden = st.catalog.length > 0 || installed.length > 0;
  const matched = new Set();
  for (const entry of st.catalog) {
    const inst = installed.find((i) => i.name === entry.name && i.version === entry.version);
    const older = installed.find((i) => i.name === entry.name && i.version !== entry.version);
    const actions = [];
    if (inst) {
      matched.add(inst.dir);
      if (inst.current) actions.push(badge("In use"));
      else actions.push(button("Use", () => usePack(inst)));
      if (inst.removable) actions.push(button("Delete", () => removePack(inst)));
    } else {
      actions.push(button(older ? "Update" : "Download", () => startDownload(entry, st.pack), !has));
    }
    box.append(row(`${packTitle(entry)} (${gb(entry.bytes)})`, entry.description || `Version ${entry.version}`, actions));
  }
  for (const inst of installed) {
    if (matched.has(inst.dir)) continue;
    const actions = [];
    if (inst.current) actions.push(badge("In use"));
    else actions.push(button("Use", () => usePack(inst)));
    if (inst.removable) actions.push(button("Delete", () => removePack(inst)));
    box.append(row(`${packTitle(inst)} ${inst.version} (${gb(inst.bytes)})`, inst.dir, actions));
  }
}

async function refresh() {
  const error = params.get("error");
  if (error) {
    params.delete("error");
    history.replaceState(null, "", window.location.pathname);
    showError(error);
    return;
  }
  try {
    const st = await invoke("status");
    if (st.downloading) {
      $("lead").textContent = "";
      show("progress");
      return;
    }
    renderPacks(st);
    if (st.pack) {
      const p = st.pack;
      $("lead").textContent = params.has("manage") ? "Knowledge packs" : "Your assistant is ready.";
      $("packLine").textContent = `${packTitle(p)} ${p.version} · ${gb(p.bytes)} · ${p.files} files`;
      const switching = st.running && st.running !== p.dir;
      $("switchNote").hidden = !switching;
      $("switchNote").textContent = switching ? `ENGRAMM restarts with the ${packTitle(p)} pack.` : "";
      $("start").textContent = st.running && !switching ? "Back to chat" : "Start chatting";
      $("installTitle").textContent = "Knowledge packs";
      $("installIntro").hidden = true;
      $("packsNote").hidden = false;
      show("ready", "install");
      return;
    }
    $("lead").textContent = st.problem || "Welcome! One more step before the first chat.";
    $("installTitle").textContent = "Install a knowledge pack";
    $("installIntro").hidden = false;
    $("packsNote").hidden = true;
    show("install");
  } catch (e) {
    showError(String(e));
  }
}

async function startChat() {
  $("start").disabled = true;
  $("starting").hidden = false;
  try {
    await invoke("start_chat");
  } catch (e) {
    $("start").disabled = false;
    $("starting").hidden = true;
    showError(String(e));
  }
}

async function startDownload(entry, current) {
  const keep = current ? `\n\nENGRAMM keeps using “${packTitle(current)}” until the download is complete; you can go on chatting meanwhile.` : "";
  const ok = window.confirm(
    `Download the knowledge pack “${packTitle(entry)}” (${gb(entry.bytes)}) from ${new URL(entry.base_url).host}?\n\n` +
    "Every file is checked (SHA-256) before ENGRAMM uses it. An interrupted download continues where it stopped." + keep);
  if (!ok) return;
  $("lead").textContent = "";
  $("barFill").style.width = "0";
  $("progressText").textContent = "Connecting …";
  show("progress");
  try {
    await invoke("download", { name: entry.name });
  } catch (e) {
    showError(String(e));
  }
}

async function usePack(inst) {
  try {
    await invoke("use_pack", { dir: inst.dir });
    await refresh();
  } catch (e) {
    showError(String(e));
  }
}

async function removePack(inst) {
  const ok = window.confirm(
    `Delete the knowledge pack “${packTitle(inst)}” (${gb(inst.bytes)}) from this computer?\n\n` +
    "You can download it again later. What ENGRAMM learned about you is not affected.");
  if (!ok) return;
  try {
    await invoke("remove_pack", { dir: inst.dir });
    await refresh();
  } catch (e) {
    showError(String(e));
  }
}

async function useFolder() {
  if (!tauri || !tauri.dialog) return showError("The folder dialog is not available.");
  const dir = await tauri.dialog.open({ directory: true, multiple: false, title: "Choose the knowledge pack folder" });
  if (!dir || Array.isArray(dir)) return;
  $("folder").disabled = true;
  $("checking").hidden = false;
  try {
    await invoke("use_folder", { path: dir });
    await refresh();
  } catch (e) {
    showError(String(e));
  } finally {
    $("folder").disabled = false;
    $("checking").hidden = true;
  }
}

if (tauri && tauri.event) {
  tauri.event.listen("pack-progress", ({ payload: p }) => {
    const frac = p.bytes_total ? Math.min(1, p.bytes_done / p.bytes_total) : 0;
    $("barFill").style.width = `${(frac * 100).toFixed(1)}%`;
    $("progressText").textContent =
      `${gb(p.bytes_done)} of ${gb(p.bytes_total)} · file ${Math.min(p.files_done + 1, p.files_total)} of ${p.files_total}` +
      (p.file ? ` (${p.file})` : "");
  });
  tauri.event.listen("pack-done", () => refresh());
  tauri.event.listen("pack-error", ({ payload }) => showError(String(payload)));
}

$("start").addEventListener("click", startChat);
$("folder").addEventListener("click", useFolder);
$("retry").addEventListener("click", () => refresh());
$("cancel").addEventListener("click", () => invoke("cancel_download").catch(() => undefined));
refresh();
