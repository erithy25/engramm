//! ENGRAMM desktop app: one window, the local chat server as a child process, and the first-run
//! setup of a knowledge pack.
//!
//! * The window opens on the bundled setup page (`setup/`). It shows the installed pack, or
//!   offers to download one from the catalog (only when the user clicks) or to use a pack
//!   folder already on this computer (works without internet).
//! * With a checked pack the app starts the server (`engramm-server --desktop --pack …`),
//!   reads the `ENGRAMM_URL=` line and moves the window to the chat page. The chat page is
//!   served by that server; to Tauri it is a remote page, so it gets no access to the app's
//!   commands. Links it opens go through the server to the system browser.
//! * The server's standard input stays open while the app runs; when it closes (the app quits
//!   or crashes), the server stops on its own.
//! * Packs can be switched later: the chat page links to `/__engramm/packs`, which the window
//!   turns into the setup page in its pack view (lite → standard, back, delete a pack not in use).
//!   Starting the chat with another pack restarts the server on it; the memory stays the same.
//!
//! No network traffic happens unless the user starts a download: no update checks, no telemetry.

use engramm_core::{fetch, pack};
use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::atomic::{AtomicBool, AtomicU16, AtomicU64, Ordering};
use std::sync::{mpsc, Arc, Mutex};
use std::time::{Duration, Instant};
use tauri::{AppHandle, Emitter, Manager, RunEvent, State, Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

const START_TIMEOUT: Duration = Duration::from_secs(90);
const LOG_LINES: usize = 60;

#[derive(Default)]
struct Server {
    child: Option<Child>,
    stdin: Option<ChildStdin>,
    log: Vec<String>,
}

struct AppState {
    server: Arc<Mutex<Server>>,
    port: Arc<AtomicU16>,
    /// the pack folder the running server was started on
    running_pack: Arc<Mutex<Option<String>>>,
    /// counts server starts and stops, so the output thread of a server that was stopped on
    /// purpose (pack switch) neither reports an error nor resets the port of its successor
    generation: Arc<AtomicU64>,
    quitting: Arc<AtomicBool>,
    cancel: Arc<AtomicBool>,
    downloading: Arc<AtomicBool>,
    setup_url: Arc<Mutex<Option<Url>>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct CatalogEntry {
    name: String,
    title: String,
    version: String,
    bytes: u64,
    base_url: String,
    manifest_sha256: String,
    #[serde(default)]
    description: String,
}

#[derive(Debug, Default, Deserialize)]
struct Catalog {
    #[serde(default)]
    packs: Vec<CatalogEntry>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
struct Settings {
    pack_dir: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize)]
struct PackInfo {
    dir: String,
    name: String,
    version: String,
    bytes: u64,
    files: usize,
}

/// A complete pack on this computer, for the pack view of the setup page.
#[derive(Debug, Clone, Serialize)]
struct Installed {
    #[serde(flatten)]
    info: PackInfo,
    /// the pack the chat starts with
    current: bool,
    /// downloaded into the app's data folder and not in use: may be deleted
    removable: bool,
}

#[derive(Debug, Serialize)]
struct Status {
    pack: Option<PackInfo>,
    problem: Option<String>,
    catalog: Vec<CatalogEntry>,
    installed: Vec<Installed>,
    /// the pack folder of the running server, if one runs
    running: Option<String>,
    data_dir: String,
    downloading: bool,
}

fn err<E: std::fmt::Display>(e: E) -> String {
    e.to_string()
}

fn data_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let d = app.path().app_data_dir().map_err(err)?;
    std::fs::create_dir_all(&d).map_err(err)?;
    Ok(d)
}

fn settings_path(app: &AppHandle) -> Result<PathBuf, String> {
    Ok(data_dir(app)?.join("settings.json"))
}

fn read_settings(app: &AppHandle) -> Settings {
    settings_path(app)
        .ok()
        .and_then(|p| std::fs::read_to_string(p).ok())
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_default()
}

fn write_settings(app: &AppHandle, s: &Settings) -> Result<(), String> {
    let path = settings_path(app)?;
    let tmp = path.with_extension("json.tmp");
    std::fs::write(&tmp, serde_json::to_vec_pretty(s).map_err(err)?).map_err(err)?;
    std::fs::rename(&tmp, &path).map_err(err)
}

fn catalog(app: &AppHandle) -> Vec<CatalogEntry> {
    app.path()
        .resource_dir()
        .ok()
        .and_then(|d| std::fs::read_to_string(d.join("catalog.json")).ok())
        .and_then(|t| serde_json::from_str::<Catalog>(&t).ok())
        .map(|c| c.packs)
        .unwrap_or_default()
}

/// A pack folder whose files are all present with the right sizes (the quick check; the
/// SHA-256 of every byte is checked after a download and when a folder is chosen).
fn check_pack(dir: &Path, deep: bool) -> Result<PackInfo, String> {
    let m = pack::Manifest::load(dir).map_err(err)?;
    let r = pack::verify(dir, &m, deep).map_err(err)?;
    if !r.complete() {
        let bad = r.to_fetch();
        let shown: Vec<&str> = bad.iter().take(5).map(|s| s.as_str()).collect();
        return Err(format!(
            "The knowledge pack in {} is incomplete or damaged ({} file(s): {}).",
            dir.display(),
            bad.len(),
            shown.join(", ")
        ));
    }
    Ok(PackInfo {
        dir: dir.display().to_string(),
        name: m.pack,
        version: m.version,
        bytes: m.bytes,
        files: m.files.len(),
    })
}

fn packs_dir(app: &AppHandle) -> Result<PathBuf, String> {
    Ok(data_dir(app)?.join("packs"))
}

/// Where packs may be, in order of preference: the folder remembered in the settings, one
/// bundled with the app, then those downloaded into the app's data folder (newest name first).
fn candidates(settings_dir: Option<PathBuf>, bundled: Option<PathBuf>, packs: Option<&Path>) -> Vec<PathBuf> {
    let mut out: Vec<PathBuf> = settings_dir.into_iter().chain(bundled).collect();
    if let Some(entries) = packs.and_then(|d| std::fs::read_dir(d).ok()) {
        let mut dirs: Vec<PathBuf> = entries.flatten().map(|e| e.path()).filter(|p| p.is_dir()).collect();
        dirs.sort();
        out.extend(dirs.into_iter().rev());
    }
    let mut seen = std::collections::HashSet::new();
    out.retain(|p| seen.insert(same_path(p)));
    out
}

/// A path in a form two spellings of the same folder agree on (Windows ignores case).
fn same_path(p: &Path) -> String {
    let s = std::fs::canonicalize(p).unwrap_or_else(|_| p.to_path_buf()).display().to_string();
    if cfg!(windows) {
        s.to_lowercase()
    } else {
        s
    }
}

fn app_candidates(app: &AppHandle) -> Vec<PathBuf> {
    candidates(
        read_settings(app).pack_dir,
        app.path().resource_dir().ok().map(|r| r.join("pack")),
        packs_dir(app).ok().as_deref(),
    )
}

/// The first complete pack among the candidates, or why none could be used.
fn first_pack(candidates: &[PathBuf]) -> (Option<PackInfo>, Option<String>) {
    let mut problem = None;
    for c in candidates {
        if !c.join(pack::MANIFEST).is_file() {
            continue;
        }
        match check_pack(c, false) {
            Ok(info) => return (Some(info), None),
            Err(e) => problem = problem.or(Some(e)),
        }
    }
    (None, problem)
}

/// Where the pack is: the folder remembered in the settings, one bundled with the app, or one
/// downloaded earlier into the app's data folder.
fn find_pack(app: &AppHandle) -> (Option<PackInfo>, Option<String>) {
    first_pack(&app_candidates(app))
}

/// Every complete pack among the candidates; `current` marks the one the chat starts with.
fn installed_packs(candidates: &[PathBuf], current: Option<&PackInfo>, packs: Option<&Path>) -> Vec<Installed> {
    let current = current.map(|c| same_path(Path::new(&c.dir)));
    let packs = packs.map(same_path);
    candidates
        .iter()
        .filter(|c| c.join(pack::MANIFEST).is_file())
        .filter_map(|c| check_pack(c, false).ok().map(|info| (same_path(c), info)))
        .map(|(key, info)| {
            let current = current.as_deref() == Some(key.as_str());
            let inside = packs.as_deref().is_some_and(|p| Path::new(&key).parent().map(same_path).as_deref() == Some(p));
            Installed { info, current, removable: inside && !current }
        })
        .collect()
}

#[tauri::command]
fn status(app: AppHandle, state: State<'_, AppState>) -> Result<Status, String> {
    let cands = app_candidates(&app);
    let (pack, problem) = first_pack(&cands);
    let installed = installed_packs(&cands, pack.as_ref(), packs_dir(&app).ok().as_deref());
    let running = if state.port.load(Ordering::SeqCst) != 0 {
        state.running_pack.lock().ok().and_then(|r| r.clone())
    } else {
        None
    };
    Ok(Status {
        pack,
        problem,
        catalog: catalog(&app),
        installed,
        running,
        data_dir: data_dir(&app)?.display().to_string(),
        downloading: state.downloading.load(Ordering::SeqCst),
    })
}

/// Makes an installed pack the one the chat starts with (the next start of the chat uses it).
#[tauri::command]
fn use_pack(app: AppHandle, dir: String) -> Result<PackInfo, String> {
    let wanted = same_path(Path::new(&dir));
    let cands = app_candidates(&app);
    let found = cands
        .into_iter()
        .find(|c| same_path(c) == wanted)
        .ok_or_else(|| format!("No installed knowledge pack at {dir}."))?;
    let info = check_pack(&found, false)?;
    write_settings(&app, &Settings { pack_dir: Some(found) })?;
    Ok(info)
}

/// Deletes a downloaded pack that is neither the current one nor the one the server runs on.
#[tauri::command]
async fn remove_pack(app: AppHandle, state: State<'_, AppState>, dir: String) -> Result<(), String> {
    let packs = packs_dir(&app)?;
    let target = PathBuf::from(&dir);
    let (current, _) = find_pack(&app);
    let running = state.running_pack.lock().map_err(err)?.clone();
    removable(&target, &packs, current.as_ref().map(|c| c.dir.as_str()), running.as_deref())?;
    let shown = target.display().to_string();
    tauri::async_runtime::spawn_blocking(move || std::fs::remove_dir_all(&target))
        .await
        .map_err(err)?
        .map_err(|e| format!("Could not delete {shown}: {e}"))?;
    Ok(())
}

/// Only a folder directly inside the app's pack folder may be deleted, and not the pack in use.
fn removable(target: &Path, packs: &Path, current: Option<&str>, running: Option<&str>) -> Result<(), String> {
    let key = same_path(target);
    let inside = target.parent().map(same_path) == Some(same_path(packs)) && target.is_dir();
    if !inside {
        return Err(format!("{} is not a pack this app downloaded; delete it yourself if you want to.", target.display()));
    }
    if current.map(|c| same_path(Path::new(c))) == Some(key.clone()) {
        return Err("This pack is in use. Switch to another pack first.".into());
    }
    if running.map(|r| same_path(Path::new(r))) == Some(key) {
        return Err("The chat still runs on this pack. Start the chat with the other pack first.".into());
    }
    Ok(())
}

#[tauri::command]
async fn use_folder(app: AppHandle, path: String) -> Result<PackInfo, String> {
    let dir = PathBuf::from(path);
    let checked = dir.clone();
    let info = tauri::async_runtime::spawn_blocking(move || check_pack(&checked, true)).await.map_err(err)??;
    write_settings(&app, &Settings { pack_dir: Some(dir) })?;
    Ok(info)
}

#[tauri::command]
fn download(app: AppHandle, state: State<'_, AppState>, name: String) -> Result<(), String> {
    let entry = catalog(&app)
        .into_iter()
        .find(|e| e.name == name)
        .ok_or_else(|| format!("No pack called {name} in this build's catalog."))?;
    if state.downloading.swap(true, Ordering::SeqCst) {
        return Err("A download is already running.".into());
    }
    state.cancel.store(false, Ordering::SeqCst);
    let dest = data_dir(&app)?.join("packs").join(format!("{}-{}", entry.name, entry.version));
    let (cancel, downloading) = (state.cancel.clone(), state.downloading.clone());
    std::thread::spawn(move || {
        let mut last = Instant::now() - Duration::from_secs(1);
        let result = fetch::fetch_pack(&entry.base_url, &entry.manifest_sha256, &dest, &cancel, &mut |p| {
            if last.elapsed() >= Duration::from_millis(200) || p.files_done == p.files_total {
                last = Instant::now();
                let _ = app.emit("pack-progress", p.clone());
            }
        });
        let outcome = result
            .map_err(err)
            .and_then(|_| check_pack(&dest, false))
            .and_then(|info| write_settings(&app, &Settings { pack_dir: Some(dest.clone()) }).map(|_| info));
        downloading.store(false, Ordering::SeqCst);
        match outcome {
            Ok(info) => {
                let _ = app.emit("pack-done", info);
            }
            Err(e) => {
                let _ = app.emit("pack-error", e);
            }
        }
    });
    Ok(())
}

#[tauri::command]
fn cancel_download(state: State<'_, AppState>) {
    state.cancel.store(true, Ordering::SeqCst);
}

/// How to start the server: the bundled sidecar, or (development) Python in ENGRAMM_HOME.
fn server_command(app: &AppHandle) -> Result<Command, String> {
    if let Ok(home) = std::env::var("ENGRAMM_HOME") {
        let home = PathBuf::from(home);
        let python = std::env::var("ENGRAMM_PYTHON").map(PathBuf::from).unwrap_or_else(|_| {
            if cfg!(windows) {
                home.join(".venv").join("Scripts").join("python.exe")
            } else {
                home.join(".venv").join("bin").join("python")
            }
        });
        let mut c = Command::new(python);
        c.args(["-u", "-m", "engramm.app"]).current_dir(&home).env("PYTHONPATH", &home);
        return Ok(c);
    }
    let dir = app.path().resource_dir().map_err(err)?.join("sidecar");
    let exe = dir.join(if cfg!(windows) { "engramm-server.exe" } else { "engramm-server" });
    if !exe.is_file() {
        return Err(format!("The ENGRAMM server is missing from this installation ({}).", exe.display()));
    }
    let mut c = Command::new(&exe);
    c.current_dir(&dir);
    Ok(c)
}

fn push_log(server: &Arc<Mutex<Server>>, line: String) {
    if let Ok(mut s) = server.lock() {
        s.log.push(line);
        let n = s.log.len();
        if n > LOG_LINES {
            s.log.drain(..n - LOG_LINES);
        }
    }
}

fn log_tail(server: &Arc<Mutex<Server>>) -> String {
    server.lock().map(|s| s.log.join("\n")).unwrap_or_default()
}

/// Moves the window to the bundled setup page, with the given query (`error=…`, `manage=1`).
fn open_setup(app: &AppHandle, state_url: &Arc<Mutex<Option<Url>>>, query: &[(&str, &str)]) {
    let Some(window) = app.get_webview_window("main") else { return };
    let Some(mut url) = state_url.lock().ok().and_then(|u| u.clone()) else { return };
    url.query_pairs_mut().clear().extend_pairs(query);
    let _ = window.navigate(url);
}

fn show_setup_error(app: &AppHandle, state_url: &Arc<Mutex<Option<Url>>>, message: &str) {
    open_setup(app, state_url, &[("error", message)]);
}

/// The chat page's link to the pack view (`/__engramm/packs` on the local server).
const PACKS_PATH: &str = "/__engramm/packs";

fn is_packs_link(url: &Url, port: u16) -> bool {
    url.scheme() == "http" && url.host_str() == Some("127.0.0.1") && port != 0 && url.port() == Some(port)
        && url.path() == PACKS_PATH
}

fn spawn_server(app: &AppHandle, state: &AppState, pack_dir: &str) -> Result<u16, String> {
    let data = data_dir(app)?;
    let cache = app.path().app_cache_dir().map_err(err)?.join("numba");
    std::fs::create_dir_all(&cache).map_err(err)?;
    let mut cmd = server_command(app)?;
    cmd.args(["--desktop", "--port", "0", "--pack", pack_dir, "--memory"])
        .arg(data.join("chat_memory.log"))
        .env("PYTHONUNBUFFERED", "1")
        .env("PYTHONIOENCODING", "utf-8")
        // UTF-8 mode: files without an explicit encoding are UTF-8 too, not the ANSI code page of Windows
        .env("PYTHONUTF8", "1")
        .env("ENGRAMM_NO_BROWSER", "1")
        .env("NUMBA_CACHE_DIR", &cache)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }
    let mut child = cmd.spawn().map_err(|e| format!("Could not start the ENGRAMM server: {e}"))?;
    let stdout = child.stdout.take().ok_or("no server output")?;
    let stderr = child.stderr.take().ok_or("no server error output")?;
    let stdin = child.stdin.take();
    {
        let mut s = state.server.lock().map_err(err)?;
        s.child = Some(child);
        s.stdin = stdin;
        s.log.clear();
    }
    let my_gen = state.generation.fetch_add(1, Ordering::SeqCst) + 1;
    let (tx, rx) = mpsc::channel::<u16>();
    let server = state.server.clone();
    let (quitting, port_cell, setup_url) = (state.quitting.clone(), state.port.clone(), state.setup_url.clone());
    let generation = state.generation.clone();
    let app_out = app.clone();
    std::thread::spawn(move || {
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Some(url) = line.strip_prefix("ENGRAMM_URL=") {
                if let Some(port) = url.rsplit(':').next().and_then(|p| p.trim().parse::<u16>().ok()) {
                    let _ = tx.send(port);
                }
            }
            push_log(&server, line);
        }
        // the server ended; unless the app is quitting or stopped it on purpose (a newer start
        // or stop happened since), that is an error worth showing
        if generation.load(Ordering::SeqCst) != my_gen {
            return;
        }
        port_cell.store(0, Ordering::SeqCst);
        if !quitting.load(Ordering::SeqCst) {
            std::thread::sleep(Duration::from_millis(300));
            if generation.load(Ordering::SeqCst) != my_gen {
                return;
            }
            let msg = format!("The ENGRAMM server stopped.\n\n{}", log_tail(&server));
            show_setup_error(&app_out, &setup_url, &msg);
        }
    });
    let server_err = state.server.clone();
    std::thread::spawn(move || {
        let mut reader = BufReader::new(stderr);
        let mut buf = String::new();
        while reader.read_line(&mut buf).map(|n| n > 0).unwrap_or(false) {
            push_log(&server_err, buf.trim_end().to_string());
            buf.clear();
        }
        let mut rest = String::new();
        let _ = reader.read_to_string(&mut rest);
    });
    match rx.recv_timeout(START_TIMEOUT) {
        Ok(port) => Ok(port),
        Err(_) => {
            stop_server(state);
            Err(format!("The ENGRAMM server did not start.\n\n{}", log_tail(&state.server)))
        }
    }
}

fn stop_server(state: &AppState) {
    state.generation.fetch_add(1, Ordering::SeqCst);
    if let Ok(mut r) = state.running_pack.lock() {
        *r = None;
    }
    let child = match state.server.lock() {
        Ok(mut s) => {
            s.stdin = None; // closing its input asks the server to stop
            s.child.take()
        }
        Err(_) => None,
    };
    if let Some(mut child) = child {
        let deadline = Instant::now() + Duration::from_secs(3);
        while Instant::now() < deadline {
            if let Ok(Some(_)) = child.try_wait() {
                return;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        let _ = child.kill();
        let _ = child.wait();
    }
    state.port.store(0, Ordering::SeqCst);
}

#[tauri::command]
async fn start_chat(app: AppHandle, window: WebviewWindow) -> Result<(), String> {
    let (pack, problem) = find_pack(&app);
    let pack = pack.ok_or_else(|| problem.unwrap_or_else(|| "No knowledge pack is installed yet.".into()))?;
    let app2 = app.clone();
    let port = tauri::async_runtime::spawn_blocking(move || {
        let state = app2.state::<AppState>();
        let running = state.port.load(Ordering::SeqCst);
        let same = state.running_pack.lock().map_err(err)?.as_deref().map(|r| same_path(Path::new(r)))
            == Some(same_path(Path::new(&pack.dir)));
        if running != 0 && same {
            return Ok(running);
        }
        if running != 0 {
            stop_server(&state); // another pack was chosen: start the server on it
        }
        let port = spawn_server(&app2, &state, &pack.dir)?;
        state.port.store(port, Ordering::SeqCst);
        *state.running_pack.lock().map_err(err)? = Some(pack.dir.clone());
        Ok::<u16, String>(port)
    })
    .await
    .map_err(err)??;
    let url = Url::parse(&format!("http://127.0.0.1:{port}/?desktop=1")).map_err(err)?;
    window.navigate(url).map_err(err)
}

/// Pages the window may show: the bundled setup page and the local chat server.
fn allowed(url: &Url, port: u16) -> bool {
    match url.scheme() {
        "tauri" | "asset" => true,
        "http" | "https" => {
            let host = url.host_str().unwrap_or("");
            host == "tauri.localhost"
                || (url.scheme() == "http" && host == "127.0.0.1" && port != 0 && url.port() == Some(port))
        }
        "about" => url.as_str() == "about:blank",
        _ => false,
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let state = AppState {
        server: Arc::new(Mutex::new(Server::default())),
        port: Arc::new(AtomicU16::new(0)),
        running_pack: Arc::new(Mutex::new(None)),
        generation: Arc::new(AtomicU64::new(0)),
        quitting: Arc::new(AtomicBool::new(false)),
        cancel: Arc::new(AtomicBool::new(false)),
        downloading: Arc::new(AtomicBool::new(false)),
        setup_url: Arc::new(Mutex::new(None)),
    };
    let nav_port = state.port.clone();
    let setup_url = state.setup_url.clone();
    let nav_setup = state.setup_url.clone();
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(state)
        .invoke_handler(tauri::generate_handler![
            status,
            use_folder,
            use_pack,
            remove_pack,
            download,
            cancel_download,
            start_chat
        ])
        .setup(move |app| {
            let handle = app.handle().clone();
            let window = WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                .title("ENGRAMM")
                .inner_size(1240.0, 820.0)
                .min_inner_size(380.0, 520.0)
                .on_navigation(move |url| {
                    let port = nav_port.load(Ordering::SeqCst);
                    if is_packs_link(url, port) {
                        // the chat page asks for the pack view: show the setup page instead
                        let (h, su) = (handle.clone(), nav_setup.clone());
                        std::thread::spawn(move || open_setup(&h, &su, &[("manage", "1")]));
                        return false;
                    }
                    allowed(url, port)
                })
                .build()?;
            if let Ok(url) = window.url() {
                if let Ok(mut s) = setup_url.lock() {
                    *s = Some(url);
                }
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building the ENGRAMM app");
    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            let state = handle.state::<AppState>();
            state.quitting.store(true, Ordering::SeqCst);
            state.cancel.store(true, Ordering::SeqCst);
            stop_server(&state);
        }
    });
}

#[cfg(test)]
mod tests {
    use super::{allowed, candidates, first_pack, installed_packs, is_packs_link, removable};
    use std::path::{Path, PathBuf};
    use tauri::Url;

    /// A complete pack folder: one file and a manifest that lists it with its size and hash.
    fn make_pack(dir: &Path, name: &str, version: &str) {
        std::fs::create_dir_all(dir).unwrap();
        let body = format!("{name} {version}");
        std::fs::write(dir.join("data.txt"), &body).unwrap();
        let sha = engramm_core::pack::sha256_file(&dir.join("data.txt")).unwrap();
        let manifest = serde_json::json!({
            "pack": name, "version": version, "bytes": body.len(),
            "files": {"data.txt": {"bytes": body.len(), "sha256": sha}}
        });
        std::fs::write(dir.join("manifest.json"), serde_json::to_vec(&manifest).unwrap()).unwrap();
    }

    fn tmp(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("engramm-app-test-{}-{name}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    #[test]
    fn the_settings_pack_comes_first_then_downloaded_packs_newest_name_first() {
        let root = tmp("order");
        let packs = root.join("packs");
        make_pack(&packs.join("lite-3.1.0"), "lite", "3.1.0");
        make_pack(&packs.join("standard-3.1.0"), "standard", "3.1.0");
        // nothing chosen: the first downloaded pack by name, newest first ("standard" > "lite")
        let c = candidates(None, None, Some(&packs));
        assert_eq!(first_pack(&c).0.unwrap().name, "standard");
        // chosen in the settings: that one, and it is listed once only
        let c = candidates(Some(packs.join("lite-3.1.0")), None, Some(&packs));
        assert_eq!(c.len(), 2);
        let (current, _) = first_pack(&c);
        assert_eq!(current.as_ref().unwrap().name, "lite");
        let inst = installed_packs(&c, current.as_ref(), Some(&packs));
        let lite = inst.iter().find(|i| i.info.name == "lite").unwrap();
        let standard = inst.iter().find(|i| i.info.name == "standard").unwrap();
        assert!(lite.current && !lite.removable);
        assert!(!standard.current && standard.removable);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn an_incomplete_download_is_not_a_pack() {
        let root = tmp("partial");
        let packs = root.join("packs");
        make_pack(&packs.join("lite-3.1.0"), "lite", "3.1.0");
        // a download that stopped before its manifest was written (fetch_pack writes it last)
        std::fs::create_dir_all(packs.join("standard-3.1.0")).unwrap();
        std::fs::write(packs.join("standard-3.1.0").join("data.txt"), "half").unwrap();
        let c = candidates(None, None, Some(&packs));
        let (current, _) = first_pack(&c);
        assert_eq!(current.as_ref().unwrap().name, "lite");
        assert_eq!(installed_packs(&c, current.as_ref(), Some(&packs)).len(), 1);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn only_a_downloaded_pack_not_in_use_may_be_deleted() {
        let root = tmp("remove");
        let packs = root.join("packs");
        let (lite, standard, elsewhere) = (packs.join("lite-3.1.0"), packs.join("standard-3.1.0"), root.join("usb-pack"));
        make_pack(&lite, "lite", "3.1.0");
        make_pack(&standard, "standard", "3.1.0");
        make_pack(&elsewhere, "lite", "3.1.0");
        let s = |p: &Path| p.display().to_string();
        assert!(removable(&lite, &packs, Some(&s(&standard)), None).is_ok());
        assert!(removable(&lite, &packs, Some(&s(&lite)), None).is_err()); // current
        assert!(removable(&lite, &packs, Some(&s(&standard)), Some(&s(&lite))).is_err()); // server runs on it
        assert!(removable(&elsewhere, &packs, Some(&s(&standard)), None).is_err()); // not ours
        assert!(removable(&packs, &packs, None, None).is_err()); // the pack folder itself
        assert!(removable(&packs.join("nope"), &packs, None, None).is_err()); // missing
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn the_pack_link_is_recognised_only_on_the_running_local_server() {
        let link = |s: &str, p: u16| is_packs_link(&Url::parse(s).unwrap(), p);
        assert!(link("http://127.0.0.1:5123/__engramm/packs", 5123));
        assert!(!link("http://127.0.0.1:5124/__engramm/packs", 5123));
        assert!(!link("http://127.0.0.1:5123/__engramm/packs", 0));
        assert!(!link("http://127.0.0.1:5123/?desktop=1", 5123));
        assert!(!link("https://example.org/__engramm/packs", 5123));
    }

    #[test]
    fn navigation_is_limited_to_the_app_and_the_local_server() {
        let ok = |s: &str, p: u16| allowed(&Url::parse(s).unwrap(), p);
        assert!(ok("tauri://localhost/index.html", 0));
        assert!(ok("http://tauri.localhost/index.html", 0));
        assert!(ok("http://127.0.0.1:5123/?desktop=1", 5123));
        assert!(!ok("http://127.0.0.1:5124/", 5123));
        assert!(!ok("http://127.0.0.1:5123/", 0));
        assert!(!ok("https://en.wikipedia.org/wiki/X", 5123));
        assert!(!ok("file:///etc/passwd", 5123));
    }
}
