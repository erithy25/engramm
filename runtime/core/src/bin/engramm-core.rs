//! Command line of the runtime core:
//!
//!   engramm-core verify DIR [--quick]     check a pack; JSON report; exit 0 when complete
//!   engramm-core normalise [--no-fillers] one message per input line → one JSON string per line
//!   engramm-core choose                   one JSON {"options","key","recent","salt"} per line → JSON string
//!   engramm-core sha256 FILE              SHA-256 of a file
//!   engramm-core fetch URL SHA256 DIR     download a pack (feature `fetch`); progress on stderr
//!   engramm-core egress [--log PATH] [--tor-dir DIR]   the network gate for the Atlas channels (feature `fetch`;
//!                                         Tor with feature `tor`)

use engramm_core::{choose, normalise, pack};
use serde::Deserialize;
use std::io::{self, BufRead, Write};
use std::path::Path;
use std::process::ExitCode;

#[derive(Deserialize)]
struct ChooseLine {
    options: Vec<String>,
    key: String,
    #[serde(default)]
    recent: Vec<String>,
    #[serde(default)]
    salt: String,
}

fn usage() -> ExitCode {
    eprintln!("usage: engramm-core verify DIR [--quick] | normalise [--no-fillers] | choose | sha256 FILE | fetch URL SHA256 DIR | egress [--log PATH]");
    ExitCode::from(2)
}

fn run() -> Result<ExitCode, Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let Some(cmd) = args.first() else { return Ok(usage()) };
    let stdin = io::stdin();
    let mut out = io::BufWriter::new(io::stdout().lock());
    match cmd.as_str() {
        "verify" => {
            let Some(dir) = args.get(1) else { return Ok(usage()) };
            let deep = !args.iter().any(|a| a == "--quick");
            let dir = Path::new(dir);
            let manifest = pack::Manifest::load(dir)?;
            let report = pack::verify(dir, &manifest, deep)?;
            writeln!(out, "{}", serde_json::to_string_pretty(&report)?)?;
            Ok(if report.complete() { ExitCode::SUCCESS } else { ExitCode::from(1) })
        }
        "normalise" => {
            let fillers = !args.iter().any(|a| a == "--no-fillers");
            for line in stdin.lock().lines() {
                writeln!(out, "{}", serde_json::to_string(&normalise(&line?, fillers))?)?;
            }
            Ok(ExitCode::SUCCESS)
        }
        "choose" => {
            for line in stdin.lock().lines() {
                let line = line?;
                if line.trim().is_empty() {
                    continue;
                }
                let c: ChooseLine = serde_json::from_str(&line)?;
                writeln!(out, "{}", serde_json::to_string(choose(&c.options, &c.key, &c.recent, &c.salt))?)?;
            }
            Ok(ExitCode::SUCCESS)
        }
        #[cfg(feature = "fetch")]
        "fetch" => {
            let (Some(url), Some(sha), Some(dir)) = (args.get(1), args.get(2), args.get(3)) else { return Ok(usage()) };
            let cancel = std::sync::atomic::AtomicBool::new(false);
            let mut last = 0u64;
            let report = engramm_core::fetch::fetch_pack(url, sha, Path::new(dir), &cancel, &mut |p| {
                if p.bytes_done >= last + (8 << 20) || p.files_done == p.files_total {
                    last = p.bytes_done;
                    eprintln!("{}/{} files, {}/{} bytes", p.files_done, p.files_total, p.bytes_done, p.bytes_total);
                }
            })?;
            writeln!(out, "{}", serde_json::to_string_pretty(&report)?)?;
            Ok(ExitCode::SUCCESS)
        }
        #[cfg(feature = "fetch")]
        "egress" => {
            let arg = |name: &str| args.iter().position(|a| a == name).and_then(|i| args.get(i + 1)).map(std::path::PathBuf::from);
            drop(out);
            engramm_core::egress::serve(arg("--log"), arg("--tor-dir"))?;
            Ok(ExitCode::SUCCESS)
        }
        "sha256" => {
            let Some(file) = args.get(1) else { return Ok(usage()) };
            writeln!(out, "{}", pack::sha256_file(Path::new(file))?)?;
            Ok(ExitCode::SUCCESS)
        }
        _ => Ok(usage()),
    }
}

fn main() -> ExitCode {
    match run() {
        Ok(code) => code,
        Err(e) => {
            eprintln!("engramm-core: {e}");
            ExitCode::from(3)
        }
    }
}
