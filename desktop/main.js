// ENGRAMM desktop app: a window around the local ENGRAMM chat server.
//
// The app starts `python -m engramm.app --no-browser --port <free port>` from the ENGRAMM folder,
// shows a loading screen until the server answers, then shows the chat. Closing the app stops the
// server. Where ENGRAMM lives is found in this order:
//   1. ENGRAMM_HOME (and optionally ENGRAMM_PYTHON) environment variables,
//   2. the folder remembered from an earlier start (settings.json in the app's user-data folder),
//   3. the folder that contains this desktop/ folder (development: `npm start`),
//   4. otherwise the app asks once with a folder dialog.
"use strict";

const { app, BrowserWindow, dialog, shell } = require("electron");
const { spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const WAIT_MS = 120000;
let server = null;
let serverLog = "";
let win = null;
let quitting = false;

function settingsPath() {
  return path.join(app.getPath("userData"), "settings.json");
}

function readSettings() {
  try { return JSON.parse(fs.readFileSync(settingsPath(), "utf8")); } catch { return {}; }
}

function writeSettings(s) {
  try {
    fs.mkdirSync(path.dirname(settingsPath()), { recursive: true });
    fs.writeFileSync(settingsPath(), JSON.stringify(s, null, 2));
  } catch { /* settings are a convenience only */ }
}

function isEngrammHome(dir) {
  return !!dir && fs.existsSync(path.join(dir, "engramm", "app", "server.py"));
}

async function findHome() {
  const candidates = [process.env.ENGRAMM_HOME, readSettings().home, path.resolve(__dirname, "..")];
  for (const c of candidates) if (isEngrammHome(c)) return c;
  const pick = await dialog.showOpenDialog({
    title: "ENGRAMM-Ordner wählen",
    message: "Wo liegt der ENGRAMM-Ordner (mit engramm/ und models/)?",
    properties: ["openDirectory"],
  });
  if (pick.canceled || !pick.filePaths.length) return null;
  const dir = pick.filePaths[0];
  if (!isEngrammHome(dir)) {
    dialog.showErrorBox("ENGRAMM", `In ${dir} liegt kein ENGRAMM (engramm/app/server.py fehlt).`);
    return null;
  }
  writeSettings({ ...readSettings(), home: dir });
  return dir;
}

function findPython(home) {
  if (process.env.ENGRAMM_PYTHON) return process.env.ENGRAMM_PYTHON;
  const venv = process.platform === "win32"
    ? path.join(home, ".venv", "Scripts", "python.exe")
    : path.join(home, ".venv", "bin", "python");
  if (fs.existsSync(venv)) return venv;
  return process.platform === "win32" ? "python" : "python3";
}

function freePort() {
  return new Promise((resolve, reject) => {
    const s = net.createServer();
    s.unref();
    s.on("error", reject);
    s.listen(0, "127.0.0.1", () => {
      const { port } = s.address();
      s.close(() => resolve(port));
    });
  });
}

function waitForServer(port) {
  const started = Date.now();
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const req = http.get({ host: "127.0.0.1", port, path: "/api/health", timeout: 1000 }, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      });
      req.on("error", retry);
      req.on("timeout", () => { req.destroy(); retry(); });
    };
    const retry = () => {
      if (server && server.exitCode !== null) return reject(new Error("Der ENGRAMM-Server hat sich beendet."));
      if (Date.now() - started > WAIT_MS) return reject(new Error("Der ENGRAMM-Server antwortet nicht."));
      setTimeout(tryOnce, 300);
    };
    tryOnce();
  });
}

function startServer(home, python, port) {
  const env = { ...process.env, PYTHONPATH: home, PYTHONUNBUFFERED: "1" };
  server = spawn(python, ["-u", "-m", "engramm.app", "--no-browser", "--port", String(port)],
    { cwd: home, env, stdio: ["ignore", "pipe", "pipe"] });
  const keep = (chunk) => { serverLog = (serverLog + chunk.toString()).slice(-4000); };
  server.stdout.on("data", keep);
  server.stderr.on("data", keep);
  server.on("exit", (code) => {
    if (!quitting && win) {
      dialog.showErrorBox("ENGRAMM", `Der ENGRAMM-Server wurde beendet (Code ${code}).\n\n${serverLog.slice(-1500)}`);
      app.quit();
    }
  });
  server.on("error", (e) => {
    dialog.showErrorBox("ENGRAMM", `Python konnte nicht gestartet werden (${python}):\n${e.message}\n\n`
      + "Setze ENGRAMM_PYTHON auf den Python-Interpreter der ENGRAMM-Umgebung.");
    app.quit();
  });
}

function createWindow() {
  win = new BrowserWindow({
    width: 1240,
    height: 820,
    minWidth: 380,
    minHeight: 520,
    title: "ENGRAMM",
    icon: path.join(__dirname, "build", "icon.png"),
    backgroundColor: "#17171c",
    titleBarStyle: process.platform === "darwin" ? "hiddenInset" : "default",
    show: false,
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true },
  });
  win.once("ready-to-show", () => win.show());
  // links (sources) open in the normal browser, never inside the app
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:\/\//.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  win.webContents.on("will-navigate", (e, url) => {
    if (!url.startsWith("http://127.0.0.1:") && !url.startsWith("file://")) { e.preventDefault(); shell.openExternal(url); }
  });
  win.on("closed", () => { win = null; });
  win.loadFile(path.join(__dirname, "loading.html"));
}

async function boot() {
  createWindow();
  const home = await findHome();
  if (!home) return app.quit();
  const python = findPython(home);
  try {
    const port = await freePort();
    startServer(home, python, port);
    await waitForServer(port);
    if (win) win.loadURL(`http://127.0.0.1:${port}/`);
  } catch (e) {
    dialog.showErrorBox("ENGRAMM", `${e.message}\n\n${serverLog.slice(-1500)}`);
    app.quit();
  }
}

function stopServer() {
  quitting = true;
  if (server && server.exitCode === null) {
    server.kill("SIGTERM");
    setTimeout(() => { if (server && server.exitCode === null) server.kill("SIGKILL"); }, 3000).unref();
  }
}

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (win) { if (win.isMinimized()) win.restore(); win.focus(); }
  });
  app.whenReady().then(boot);
  app.on("before-quit", stopServer);
  app.on("window-all-closed", () => app.quit());
}
