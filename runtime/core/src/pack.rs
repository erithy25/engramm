//! Knowledge packs: a folder with the reading, the counted models and the fact bank, plus
//! `manifest.json` (written by `experiments/pack_build.py`) listing every file with its size
//! and SHA-256. The app starts only on a pack whose files all match the manifest.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fmt;
use std::fs::File;
use std::io::{self, Read};
use std::path::{Component, Path, PathBuf};

pub const MANIFEST: &str = "manifest.json";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct FileEntry {
    pub bytes: u64,
    pub sha256: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub pack: String,
    pub version: String,
    #[serde(default)]
    pub built: String,
    pub bytes: u64,
    pub files: BTreeMap<String, FileEntry>,
    #[serde(default)]
    pub licenses: BTreeMap<String, String>,
    #[serde(default)]
    pub info: serde_json::Value,
}

#[derive(Debug)]
pub enum PackError {
    Io(PathBuf, io::Error),
    Json(String),
    Invalid(String),
}

impl fmt::Display for PackError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PackError::Io(p, e) => write!(f, "{}: {}", p.display(), e),
            PackError::Json(e) => write!(f, "manifest is not valid JSON: {e}"),
            PackError::Invalid(e) => write!(f, "manifest is invalid: {e}"),
        }
    }
}

impl std::error::Error for PackError {}

/// A path from the manifest, checked to stay inside the pack folder: relative, forward
/// slashes, no empty, "." or ".." parts, no drive letters.
pub fn safe_relative(rel: &str) -> Result<PathBuf, PackError> {
    if rel.is_empty() || rel.starts_with('/') || rel.contains('\\') || rel.contains(':') || rel.contains('\0') {
        return Err(PackError::Invalid(format!("unsafe path {rel:?}")));
    }
    let mut out = PathBuf::new();
    for part in rel.split('/') {
        if part.is_empty() || part == "." || part == ".." {
            return Err(PackError::Invalid(format!("unsafe path {rel:?}")));
        }
        out.push(part);
    }
    if out.components().any(|c| !matches!(c, Component::Normal(_))) {
        return Err(PackError::Invalid(format!("unsafe path {rel:?}")));
    }
    Ok(out)
}

fn is_hex64(s: &str) -> bool {
    s.len() == 64 && s.bytes().all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
}

impl Manifest {
    /// Parses and checks a manifest: safe paths, lower-case hex digests, sizes that add up.
    pub fn from_json(text: &str) -> Result<Manifest, PackError> {
        let m: Manifest = serde_json::from_str(text).map_err(|e| PackError::Json(e.to_string()))?;
        if m.pack.is_empty() || m.version.is_empty() {
            return Err(PackError::Invalid("pack name and version are required".into()));
        }
        if m.files.is_empty() {
            return Err(PackError::Invalid("no files".into()));
        }
        let mut total: u64 = 0;
        for (rel, entry) in &m.files {
            safe_relative(rel)?;
            if rel == MANIFEST {
                return Err(PackError::Invalid("the manifest cannot list itself".into()));
            }
            if !is_hex64(&entry.sha256) {
                return Err(PackError::Invalid(format!("bad sha256 for {rel}")));
            }
            total = total
                .checked_add(entry.bytes)
                .ok_or_else(|| PackError::Invalid("sizes overflow".into()))?;
        }
        if total != m.bytes {
            return Err(PackError::Invalid(format!("sizes add up to {total}, manifest says {}", m.bytes)));
        }
        Ok(m)
    }

    pub fn load(dir: &Path) -> Result<Manifest, PackError> {
        let path = dir.join(MANIFEST);
        let text = std::fs::read_to_string(&path).map_err(|e| PackError::Io(path.clone(), e))?;
        Manifest::from_json(&text)
    }
}

/// SHA-256 of a byte string, lower-case hex.
pub fn sha256_hex(data: &[u8]) -> String {
    hex(&Sha256::digest(data))
}

/// SHA-256 of a file, read in 4 MiB pieces, lower-case hex.
pub fn sha256_file(path: &Path) -> io::Result<String> {
    let mut f = File::open(path)?;
    let mut h = Sha256::new();
    let mut buf = vec![0u8; 1 << 22];
    loop {
        let n = f.read(&mut buf)?;
        if n == 0 {
            break;
        }
        h.update(&buf[..n]);
    }
    Ok(hex(&h.finalize()))
}

fn hex(bytes: &[u8]) -> String {
    const DIGITS: &[u8; 16] = b"0123456789abcdef";
    let mut s = String::with_capacity(bytes.len() * 2);
    for b in bytes {
        s.push(DIGITS[(b >> 4) as usize] as char);
        s.push(DIGITS[(b & 15) as usize] as char);
    }
    s
}

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct Report {
    pub pack: String,
    pub version: String,
    pub ok: Vec<String>,
    pub missing: Vec<String>,
    pub wrong_size: Vec<String>,
    pub wrong_hash: Vec<String>,
    /// Bytes of the files that still have to be fetched (missing or wrong).
    pub bytes_to_fetch: u64,
}

impl Report {
    pub fn complete(&self) -> bool {
        self.missing.is_empty() && self.wrong_size.is_empty() && self.wrong_hash.is_empty()
    }

    /// Files that a download still has to fetch, in manifest order.
    pub fn to_fetch(&self) -> Vec<String> {
        let mut v: Vec<String> =
            self.missing.iter().chain(&self.wrong_size).chain(&self.wrong_hash).cloned().collect();
        v.sort();
        v
    }
}

/// Checks every file of the pack in `dir` against `manifest`: presence and size always,
/// the SHA-256 when `deep` (reads every byte; the quick check is for every start, the deep
/// one after a download or on request).
pub fn verify(dir: &Path, manifest: &Manifest, deep: bool) -> Result<Report, PackError> {
    let mut r = Report { pack: manifest.pack.clone(), version: manifest.version.clone(), ..Report::default() };
    for (rel, entry) in &manifest.files {
        let path = dir.join(safe_relative(rel)?);
        match std::fs::metadata(&path) {
            Err(e) if e.kind() == io::ErrorKind::NotFound => {
                r.missing.push(rel.clone());
                r.bytes_to_fetch += entry.bytes;
            }
            Err(e) => return Err(PackError::Io(path, e)),
            Ok(meta) if !meta.is_file() || meta.len() != entry.bytes => {
                r.wrong_size.push(rel.clone());
                r.bytes_to_fetch += entry.bytes;
            }
            Ok(_) => {
                if deep {
                    let got = sha256_file(&path).map_err(|e| PackError::Io(path.clone(), e))?;
                    if got != entry.sha256 {
                        r.wrong_hash.push(rel.clone());
                        r.bytes_to_fetch += entry.bytes;
                        continue;
                    }
                }
                r.ok.push(rel.clone());
            }
        }
    }
    Ok(r)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    fn tmpdir(name: &str) -> PathBuf {
        let d = std::env::temp_dir().join(format!("engramm-core-test-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&d);
        std::fs::create_dir_all(&d).unwrap();
        d
    }

    fn write(dir: &Path, rel: &str, data: &[u8]) {
        let p = dir.join(rel);
        std::fs::create_dir_all(p.parent().unwrap()).unwrap();
        File::create(p).unwrap().write_all(data).unwrap();
    }

    fn manifest_for(files: &[(&str, &[u8])]) -> String {
        let mut map = serde_json::Map::new();
        let mut total = 0u64;
        for (rel, data) in files {
            total += data.len() as u64;
            map.insert(rel.to_string(), serde_json::json!({"bytes": data.len(), "sha256": sha256_hex(data)}));
        }
        serde_json::json!({"pack": "t", "version": "1", "built": "", "bytes": total, "files": map}).to_string()
    }

    #[test]
    fn safe_paths() {
        assert!(safe_relative("nlp/pos.json").is_ok());
        for bad in ["", "/etc/passwd", "../x", "a/../b", "a//b", "./a", "c:/x", "a\\b"] {
            assert!(safe_relative(bad).is_err(), "{bad}");
        }
    }

    #[test]
    fn sha256_known_value() {
        assert_eq!(sha256_hex(b"abc"), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad");
    }

    #[test]
    fn verify_detects_every_kind_of_damage() {
        let d = tmpdir("verify");
        let files: [(&str, &[u8]); 4] =
            [("a.bin", b"hello"), ("nlp/b.json", b"{}"), ("c.txt", b"data"), ("d.txt", b"more")];
        let m = Manifest::from_json(&manifest_for(&files)).unwrap();
        write(&d, "a.bin", b"hello");
        write(&d, "nlp/b.json", b"{}");
        write(&d, "c.txt", b"dat");
        write(&d, "d.txt", b"MORE");
        let quick = verify(&d, &m, false).unwrap();
        assert_eq!(quick.wrong_size, vec!["c.txt"]);
        assert!(quick.ok.contains(&"d.txt".to_string()));
        let deep = verify(&d, &m, true).unwrap();
        assert_eq!(deep.ok, vec!["a.bin", "nlp/b.json"]);
        assert_eq!(deep.wrong_size, vec!["c.txt"]);
        assert_eq!(deep.wrong_hash, vec!["d.txt"]);
        assert_eq!(deep.bytes_to_fetch, 8);
        assert!(!deep.complete());
        std::fs::remove_file(d.join("a.bin")).unwrap();
        let r = verify(&d, &m, true).unwrap();
        assert_eq!(r.missing, vec!["a.bin"]);
        assert_eq!(r.to_fetch(), vec!["a.bin", "c.txt", "d.txt"]);
        let _ = std::fs::remove_dir_all(&d);
    }

    #[test]
    fn manifest_checks() {
        let good = manifest_for(&[("a", b"x")]);
        assert!(Manifest::from_json(&good).is_ok());
        let mut v: serde_json::Value = serde_json::from_str(&good).unwrap();
        v["bytes"] = serde_json::json!(2);
        assert!(Manifest::from_json(&v.to_string()).is_err());
        let mut v: serde_json::Value = serde_json::from_str(&good).unwrap();
        v["files"]["a"]["sha256"] = serde_json::json!("ABC");
        assert!(Manifest::from_json(&v.to_string()).is_err());
        let unsafe_path = manifest_for(&[("../a", b"x")]);
        assert!(Manifest::from_json(&unsafe_path).is_err());
        assert!(Manifest::from_json("{").is_err());
    }
}
