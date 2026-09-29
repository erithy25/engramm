// First-run and start page of the ENGRAMM desktop app (runs inside the app window only).
"use strict";

const tauri = window.__TAURI__;
const $ = (id) => document.getElementById(id);
const sections = ["error", "ready", "install", "progress"];

function show(...ids) {
  for (const s of sections) $(s).hidden = !ids.includes(s);
}

function gb(bytes) {
  return bytes >= 1e9 ? `${(bytes / 1e9).toFixed(2)} GB` : `${Math.max(1, Math.round(bytes / 1e6))} MB`;
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

function renderCatalog(catalog) {
  const box = $("catalog");
  box.textContent = "";
  $("noCatalog").hidden = catalog.length > 0;
  for (const entry of catalog) {
    const row = document.createElement("div");
    row.className = "pack";
    const info = document.createElement("div");
    const title = document.createElement("b");
    title.textContent = `${entry.title} (${gb(entry.bytes)})`;
    const desc = document.createElement("span");
    desc.className = "small muted";
    desc.textContent = entry.description || `Version ${entry.version}`;
    info.append(title, desc);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "primary";
    btn.textContent = "Download";
    btn.title = `Downloads ${gb(entry.bytes)} from ${new URL(entry.base_url).host}`;
    btn.addEventListener("click", () => startDownload(entry));
    row.append(info, btn);
    box.append(row);
  }
}

async function refresh() {
  const params = new URLSearchParams(window.location.search);
  const error = params.get("error");
  if (error) {
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
    if (st.pack) {
      $("lead").textContent = "Your assistant is ready.";
      $("packLine").textContent =
        `Knowledge pack “${st.pack.name}” ${st.pack.version} · ${gb(st.pack.bytes)} · ${st.pack.files} files`;
      show("ready");
      return;
    }
    $("lead").textContent = st.problem || "Welcome! One more step before the first chat.";
    renderCatalog(st.catalog);
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

async function startDownload(entry) {
  const ok = window.confirm(
    `Download the knowledge pack “${entry.title}” (${gb(entry.bytes)}) from ${new URL(entry.base_url).host}?\n\n` +
    "Every file is checked (SHA-256) before ENGRAMM uses it. An interrupted download continues where it stopped.");
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
