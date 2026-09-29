//! Downloading a knowledge pack (feature `fetch`): only after the user agreed, only from the
//! address in the app's catalog, and only a manifest whose SHA-256 the catalog pins.
//!
//! Release assets are flat (GitHub release assets have no folders): the file `nlp/pos.json`
//! of a pack is the asset `nlp__pos.json`. Each file is written to `<file>.part`, resumed with
//! an HTTP range request after an interruption, checked against size and SHA-256 and only then
//! renamed into place, so a pack folder never holds a file that is wrong but looks finished.

use crate::pack::{safe_relative, sha256_hex, verify, Manifest, PackError, Report, MANIFEST};
use sha2::{Digest, Sha256};
use std::fmt;
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom, Write};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Duration;

/// The release asset name of a pack file.
pub fn asset_name(rel: &str) -> String {
    rel.replace('/', "__")
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct Progress {
    pub file: String,
    pub files_done: usize,
    pub files_total: usize,
    pub bytes_done: u64,
    pub bytes_total: u64,
}

#[derive(Debug)]
pub enum FetchError {
    Http(String),
    Io(PathBuf, io::Error),
    Pack(PackError),
    ManifestMismatch { expected: String, got: String },
    FileMismatch(String),
    Cancelled,
}

impl fmt::Display for FetchError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            FetchError::Http(e) => write!(f, "download failed: {e}"),
            FetchError::Io(p, e) => write!(f, "{}: {}", p.display(), e),
            FetchError::Pack(e) => write!(f, "{e}"),
            FetchError::ManifestMismatch { expected, got } => {
                write!(f, "the pack manifest is not the expected one (SHA-256 {got}, expected {expected})")
            }
            FetchError::FileMismatch(rel) => write!(f, "{rel} does not match the manifest after download"),
            FetchError::Cancelled => write!(f, "download cancelled"),
        }
    }
}

impl std::error::Error for FetchError {}

impl From<PackError> for FetchError {
    fn from(e: PackError) -> Self {
        FetchError::Pack(e)
    }
}

fn agent() -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_secs(20))
        .timeout_read(Duration::from_secs(60))
        .try_proxy_from_env(true)
        .user_agent(concat!("engramm-core/", env!("CARGO_PKG_VERSION")))
        .build()
}

fn join_url(base: &str, name: &str) -> String {
    if base.ends_with('/') {
        format!("{base}{name}")
    } else {
        format!("{base}/{name}")
    }
}

/// Downloads the manifest and checks it against the pinned SHA-256.
pub fn fetch_manifest(base_url: &str, expected_sha256: &str) -> Result<(Manifest, Vec<u8>), FetchError> {
    let resp = agent()
        .get(&join_url(base_url, MANIFEST))
        .call()
        .map_err(|e| FetchError::Http(e.to_string()))?;
    let mut body = Vec::new();
    resp.into_reader()
        .take(16 << 20)
        .read_to_end(&mut body)
        .map_err(|e| FetchError::Http(e.to_string()))?;
    let got = sha256_hex(&body);
    if !got.eq_ignore_ascii_case(expected_sha256) {
        return Err(FetchError::ManifestMismatch { expected: expected_sha256.to_string(), got });
    }
    let text = String::from_utf8(body.clone()).map_err(|e| FetchError::Http(e.to_string()))?;
    Ok((Manifest::from_json(&text)?, body))
}

fn part_path(path: &Path) -> PathBuf {
    let mut name = path.file_name().map(|n| n.to_os_string()).unwrap_or_default();
    name.push(".part");
    path.with_file_name(name)
}

/// Fetches one file into `<dest>.part` (resuming), checks it and renames it into place.
fn fetch_file(
    agent: &ureq::Agent,
    url: &str,
    dest: &Path,
    bytes: u64,
    sha256: &str,
    cancel: &AtomicBool,
    on_bytes: &mut dyn FnMut(u64),
) -> Result<bool, FetchError> {
    if let Some(parent) = dest.parent() {
        fs::create_dir_all(parent).map_err(|e| FetchError::Io(parent.to_path_buf(), e))?;
    }
    let part = part_path(dest);
    let mut have = fs::metadata(&part).map(|m| m.len()).unwrap_or(0);
    if have > bytes {
        fs::remove_file(&part).map_err(|e| FetchError::Io(part.clone(), e))?;
        have = 0;
    }
    let mut hasher = Sha256::new();
    if have > 0 {
        // hash what is already there, then continue after it
        let mut f = File::open(&part).map_err(|e| FetchError::Io(part.clone(), e))?;
        let mut buf = vec![0u8; 1 << 20];
        let mut left = have;
        while left > 0 {
            let n = f.read(&mut buf).map_err(|e| FetchError::Io(part.clone(), e))?;
            if n == 0 {
                break;
            }
            hasher.update(&buf[..n]);
            left = left.saturating_sub(n as u64);
        }
        on_bytes(have);
    }
    if have < bytes {
        let mut req = agent.get(url);
        if have > 0 {
            req = req.set("Range", &format!("bytes={have}-"));
        }
        let resp = req.call().map_err(|e| FetchError::Http(format!("{url}: {e}")))?;
        let resumed = resp.status() == 206;
        let mut out = if resumed {
            let mut f = OpenOptions::new().append(true).open(&part).map_err(|e| FetchError::Io(part.clone(), e))?;
            f.seek(SeekFrom::End(0)).map_err(|e| FetchError::Io(part.clone(), e))?;
            f
        } else {
            // the server sent the whole file: start over
            if have > 0 {
                on_bytes(0u64.wrapping_sub(have));
                hasher = Sha256::new();
                have = 0;
            }
            File::create(&part).map_err(|e| FetchError::Io(part.clone(), e))?
        };
        let mut reader = resp.into_reader().take(bytes - have);
        let mut buf = vec![0u8; 1 << 20];
        loop {
            if cancel.load(Ordering::Relaxed) {
                out.flush().map_err(|e| FetchError::Io(part.clone(), e))?;
                return Err(FetchError::Cancelled);
            }
            let n = reader.read(&mut buf).map_err(|e| FetchError::Http(format!("{url}: {e}")))?;
            if n == 0 {
                break;
            }
            out.write_all(&buf[..n]).map_err(|e| FetchError::Io(part.clone(), e))?;
            hasher.update(&buf[..n]);
            have += n as u64;
            on_bytes(n as u64);
        }
        out.sync_all().map_err(|e| FetchError::Io(part.clone(), e))?;
    }
    let digest: String = hasher.finalize().iter().map(|b| format!("{b:02x}")).collect();
    if have != bytes || digest != sha256 {
        let _ = fs::remove_file(&part);
        return Ok(false);
    }
    fs::rename(&part, dest).map_err(|e| FetchError::Io(dest.to_path_buf(), e))?;
    Ok(true)
}

/// Brings the pack in `dest` up to the manifest at `base_url` (pinned by `manifest_sha256`):
/// fetches what is missing or wrong, checks everything, writes the manifest last.
/// `progress` is called after every piece; `cancel` stops between pieces.
pub fn fetch_pack(
    base_url: &str,
    manifest_sha256: &str,
    dest: &Path,
    cancel: &AtomicBool,
    progress: &mut dyn FnMut(&Progress),
) -> Result<Report, FetchError> {
    let (manifest, raw) = fetch_manifest(base_url, manifest_sha256)?;
    fs::create_dir_all(dest).map_err(|e| FetchError::Io(dest.to_path_buf(), e))?;
    let before = verify(dest, &manifest, true)?;
    let todo = before.to_fetch();
    let mut p = Progress {
        file: String::new(),
        files_done: 0,
        files_total: todo.len(),
        bytes_done: 0,
        bytes_total: before.bytes_to_fetch,
    };
    progress(&p);
    let agent = agent();
    for rel in &todo {
        let entry = &manifest.files[rel];
        let path = dest.join(safe_relative(rel)?);
        if path.exists() {
            fs::remove_file(&path).map_err(|e| FetchError::Io(path.clone(), e))?;
        }
        p.file = rel.clone();
        let url = join_url(base_url, &asset_name(rel));
        let mut ok = false;
        for _attempt in 0..2 {
            let start = p.bytes_done;
            let res = fetch_file(&agent, &url, &path, entry.bytes, &entry.sha256, cancel, &mut |n| {
                p.bytes_done = p.bytes_done.wrapping_add(n);
                progress(&p);
            });
            match res {
                Ok(true) => {
                    ok = true;
                    break;
                }
                Ok(false) => p.bytes_done = start,
                Err(e) => return Err(e),
            }
        }
        if !ok {
            return Err(FetchError::FileMismatch(rel.clone()));
        }
        p.files_done += 1;
        progress(&p);
    }
    let after = verify(dest, &manifest, true)?;
    if !after.complete() {
        return Err(FetchError::FileMismatch(after.to_fetch().join(", ")));
    }
    let mpath = dest.join(MANIFEST);
    fs::write(&mpath, raw).map_err(|e| FetchError::Io(mpath, e))?;
    Ok(after)
}
