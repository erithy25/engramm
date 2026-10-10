//! The one way out to the network for the desktop app (feature `fetch`; docs/SPEC_ATLAS.md).
//!
//! `engramm-core egress [--log PATH]` reads one JSON request per line on stdin and answers with
//! one JSON line on stdout. The rules are the same as in `engramm/web/egress.py`: https only
//! (loopback http only when a test allows it), the host must be allowed for the request, no
//! private addresses for the web search, redirects only to allowed hosts, GET only, no cookies,
//! a fixed user agent (a browser's for the web search: search engines and many sites refuse
//! other clients), only a few harmless extra headers, and hard limits on size and time. Each
//! fetch is logged (what was fetched, never why).

use serde::{Deserialize, Serialize};
use std::fs::OpenOptions;
use std::io::{self, BufRead, Read, Write};
use std::net::IpAddr;
use std::path::PathBuf;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

pub const USER_AGENT: &str = "ENGRAMM/3.1 (+offline assistant)";
/// The web search reads search engines and the pages they list, which refuse unknown clients.
pub const BROWSER_USER_AGENT: &str =
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36";
const CHANNELS: [&str; 3] = ["shelf", "feeds", "search"];
/// The only headers a request may add (lower case): content negotiation and a search API key.
const HEADERS: [&str; 3] = ["accept", "accept-language", "x-subscription-token"];

#[derive(Debug, Deserialize)]
pub struct EgressRequest {
    #[serde(default)]
    pub id: u64,
    pub channel: String,
    pub url: String,
    #[serde(default)]
    pub what: String,
    #[serde(default)]
    pub allow_hosts: Vec<String>,
    #[serde(default)]
    pub range: Option<(u64, u64)>,
    #[serde(default)]
    pub max_bytes: Option<u64>,
    #[serde(default)]
    pub headers: Vec<(String, String)>,
    #[serde(default)]
    pub timeout: Option<f64>,
    #[serde(default)]
    pub allow_loopback: bool,
}

#[derive(Debug, Serialize, Default)]
pub struct EgressResponse {
    pub id: u64,
    pub ok: bool,
    #[serde(skip_serializing_if = "is_zero")]
    pub status: u16,
    #[serde(skip_serializing_if = "is_zero_u64")]
    pub bytes: u64,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub body_b64: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub error: String,
    pub via: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub final_host: String,
    #[serde(skip_serializing_if = "String::is_empty")]
    pub content_type: String,
}

fn is_zero(v: &u16) -> bool {
    *v == 0
}
fn is_zero_u64(v: &u64) -> bool {
    *v == 0
}

/// (scheme, host) of a URL, host lower-cased and without brackets or port.
pub fn split_url(url: &str) -> Option<(String, String)> {
    let (scheme, rest) = url.split_once("://")?;
    let authority = rest.split(['/', '?', '#']).next().unwrap_or("");
    if authority.contains('@') {
        return None; // credentials in URLs are refused
    }
    let host = if let Some(stripped) = authority.strip_prefix('[') {
        stripped.split(']').next().unwrap_or("").to_string()
    } else {
        authority.rsplit_once(':').map(|(h, p)| if p.chars().all(|c| c.is_ascii_digit()) { h } else { authority })
            .unwrap_or(authority).to_string()
    };
    Some((scheme.to_ascii_lowercase(), host.to_ascii_lowercase()))
}

pub fn host_allowed(host: &str, allow: &[String]) -> bool {
    if host.is_empty() {
        return false;
    }
    allow.iter().any(|a| {
        let a = a.trim_start_matches('.').to_ascii_lowercase();
        a == "*" || host == a || host.ends_with(&format!(".{a}"))
    })
}

/// Loopback, private, link-local and reserved addresses, localhost and *.local / *.internal.
pub fn is_private_host(host: &str) -> bool {
    let h = host.trim_matches(|c| c == '[' || c == ']');
    if h == "localhost" || [".localhost", ".local", ".internal", ".lan", ".home", ".corp"].iter().any(|s| h.ends_with(s)) {
        return true;
    }
    match h.parse::<IpAddr>() {
        Ok(IpAddr::V4(v4)) => {
            v4.is_private() || v4.is_loopback() || v4.is_link_local() || v4.is_unspecified() || v4.is_broadcast()
                || v4.is_documentation() || v4.octets()[0] == 0 || (v4.octets()[0] == 100 && (v4.octets()[1] & 0xc0) == 64)
        }
        Ok(IpAddr::V6(v6)) => {
            let s = v6.segments();
            v6.is_loopback() || v6.is_unspecified() || (s[0] & 0xfe00) == 0xfc00 || (s[0] & 0xffc0) == 0xfe80
                || v6.to_ipv4_mapped().map(|v4| v4.is_private() || v4.is_loopback()).unwrap_or(false)
        }
        Err(_) => false,
    }
}

/// The request rules; `Err(reason)` when the fetch must not happen.
pub fn check(req: &EgressRequest, url: &str) -> Result<(), String> {
    if !CHANNELS.contains(&req.channel.as_str()) {
        return Err(format!("unknown channel: {}", req.channel));
    }
    let Some((scheme, host)) = split_url(url) else { return Err("not a valid URL (or credentials in it)".into()) };
    let loopback = req.allow_loopback && matches!(host.as_str(), "127.0.0.1" | "localhost" | "::1");
    if scheme != "https" && !(loopback && scheme == "http") {
        return Err("only https is allowed".into());
    }
    if !loopback && req.channel == "search" && is_private_host(&host) {
        return Err(format!("private address not allowed: {host}"));
    }
    if !loopback && !host_allowed(&host, &req.allow_hosts) {
        return Err(format!("host not allowed: {host}"));
    }
    for (name, value) in &req.headers {
        if !HEADERS.contains(&name.to_ascii_lowercase().as_str()) {
            return Err(format!("header not allowed: {name}"));
        }
        if value.len() > 200 || value.chars().any(|c| c.is_control()) {
            return Err(format!("bad value for header {name}"));
        }
    }
    Ok(())
}

const B64: &[u8; 64] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

pub fn base64(data: &[u8]) -> String {
    let mut out = String::with_capacity((data.len() + 2) / 3 * 4);
    for chunk in data.chunks(3) {
        let b = [chunk[0], *chunk.get(1).unwrap_or(&0), *chunk.get(2).unwrap_or(&0)];
        let n = (b[0] as u32) << 16 | (b[1] as u32) << 8 | b[2] as u32;
        out.push(B64[(n >> 18) as usize & 63] as char);
        out.push(B64[(n >> 12) as usize & 63] as char);
        out.push(if chunk.len() > 1 { B64[(n >> 6) as usize & 63] as char } else { '=' });
        out.push(if chunk.len() > 2 { B64[n as usize & 63] as char } else { '=' });
    }
    out
}

/// "2026-10-01T18:30:00+00:00" for a Unix time (UTC; the civil-from-days algorithm).
pub fn iso_utc(secs: u64) -> String {
    let days = (secs / 86400) as i64;
    let rem = secs % 86400;
    let z = days + 719468;
    let era = z.div_euclid(146097);
    let doe = z - era * 146097;
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
    let y = yoe + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = doy - (153 * mp + 2) / 5 + 1;
    let m = if mp < 10 { mp + 3 } else { mp - 9 };
    let y = if m <= 2 { y + 1 } else { y };
    format!("{y:04}-{m:02}-{d:02}T{:02}:{:02}:{:02}+00:00", rem / 3600, rem % 3600 / 60, rem % 60)
}

fn agent(timeout: f64, loopback: bool, user_agent: &str) -> ureq::Agent {
    let timeout = timeout.clamp(1.0, 120.0);
    ureq::AgentBuilder::new()
        .timeout_connect(Duration::from_secs_f64(timeout.min(20.0)))
        .timeout(Duration::from_secs_f64(timeout))
        .redirects(0)
        .try_proxy_from_env(!loopback)
        .user_agent(user_agent)
        .build()
}

/// A transport error without the URL (for the web search it holds the search words, and the
/// network log must never hold a question).
fn describe(e: &ureq::Error) -> String {
    let text = match e {
        ureq::Error::Transport(t) => match t.message() {
            Some(m) => format!("{}: {m}", t.kind()),
            None => t.kind().to_string(),
        },
        ureq::Error::Status(code, _) => format!("HTTP {code}"),
    };
    text.chars().take(200).collect()
}

/// One fetch with the rules, following up to five redirects to allowed hosts.
pub fn fetch(req: &EgressRequest) -> EgressResponse {
    let mut resp = EgressResponse { id: req.id, via: "direct".into(), ..Default::default() };
    let user_agent = if req.channel == "search" { BROWSER_USER_AGENT } else { USER_AGENT };
    let limit = req.max_bytes.unwrap_or(2 << 20).min(64 << 20);
    let mut url = req.url.clone();
    for _ in 0..6 {
        if let Err(e) = check(req, &url) {
            resp.error = e;
            return resp;
        }
        let host = split_url(&url).map(|(_, h)| h).unwrap_or_default();
        let loopback = req.allow_loopback && matches!(host.as_str(), "127.0.0.1" | "localhost" | "::1");
        let mut call = agent(req.timeout.unwrap_or(30.0), loopback, user_agent).get(&url).set("Accept-Encoding", "identity");
        for (name, value) in &req.headers {
            call = call.set(name, value);
        }
        if let Some((a, b)) = req.range {
            call = call.set("Range", &format!("bytes={a}-{b}"));
        }
        let r = match call.call() {
            Ok(r) => r,
            Err(ureq::Error::Status(code, r)) if !(300..400).contains(&code) => {
                resp.status = code;
                resp.error = format!("HTTP {code}");
                let _ = r;
                return resp;
            }
            Err(ureq::Error::Status(_, r)) => r,
            Err(e) => {
                resp.error = describe(&e);
                return resp;
            }
        };
        let code = r.status();
        if (300..400).contains(&code) {
            let Some(loc) = r.header("Location").map(str::to_string) else {
                resp.status = code;
                resp.error = "redirect without a location".into();
                return resp;
            };
            url = if loc.starts_with("http://") || loc.starts_with("https://") {
                loc
            } else if loc.starts_with('/') {
                // a path on the same server: keep scheme, host and port
                let (scheme, rest) = url.split_once("://").unwrap_or(("https", ""));
                let authority = rest.split(['/', '?', '#']).next().unwrap_or("");
                format!("{scheme}://{authority}{loc}")
            } else {
                resp.error = "relative redirect without a path".into();
                return resp;
            };
            continue;
        }
        resp.status = code;
        resp.final_host = host;
        resp.content_type = r.header("Content-Type").unwrap_or("").to_string();
        let mut body = Vec::new();
        match r.into_reader().take(limit + 1).read_to_end(&mut body) {
            Ok(_) if body.len() as u64 > limit => {
                resp.error = format!("response larger than {limit} bytes");
                return resp;
            }
            Ok(_) => {
                resp.ok = true;
                resp.bytes = body.len() as u64;
                resp.body_b64 = base64(&body);
                return resp;
            }
            Err(e) => {
                resp.error = format!("read failed: {e}");
                return resp;
            }
        }
    }
    resp.error = "too many redirects".into();
    resp
}

fn log_line(path: &Option<PathBuf>, req: &EgressRequest, resp: &EgressResponse) {
    let Some(p) = path else { return };
    let host = if resp.final_host.is_empty() { split_url(&req.url).map(|(_, h)| h).unwrap_or_default() } else {
        resp.final_host.clone()
    };
    let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
    let mut entry = serde_json::json!({"ts": iso_utc(now), "channel": req.channel, "host": host, "what": req.what,
        "bytes": resp.bytes, "status": resp.status, "via": resp.via, "ok": resp.ok});
    if !resp.ok {
        entry["error"] = serde_json::Value::String(resp.error.clone());
    }
    if let Ok(mut f) = OpenOptions::new().create(true).append(true).open(p) {
        let _ = writeln!(f, "{entry}");
    }
}

/// The stdin/stdout service; ends when stdin closes. `{"op": "status"}` answers that the service runs.
pub fn serve(log: Option<PathBuf>) -> io::Result<()> {
    let stdin = io::stdin();
    let mut out = io::stdout().lock();
    for line in stdin.lock().lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        if let Ok(op) = serde_json::from_str::<serde_json::Value>(&line) {
            if let Some(name) = op.get("op").and_then(|v| v.as_str()) {
                let id = op.get("id").and_then(|v| v.as_u64()).unwrap_or(0);
                let reply = match name {
                    "status" => serde_json::json!({"id": id, "ok": true, "via": "-"}),
                    _ => serde_json::json!({"id": id, "ok": false, "error": format!("unknown op: {name}"), "via": "-"}),
                };
                writeln!(out, "{reply}")?;
                out.flush()?;
                continue;
            }
        }
        let resp = match serde_json::from_str::<EgressRequest>(&line) {
            Ok(req) => {
                let r = fetch(&req);
                log_line(&log, &req, &r);
                r
            }
            Err(e) => EgressResponse { ok: false, error: format!("bad request: {e}"), via: "-".into(), ..Default::default() },
        };
        writeln!(out, "{}", serde_json::to_string(&resp)?)?;
        out.flush()?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn req(channel: &str, url: &str, allow: &[&str]) -> EgressRequest {
        EgressRequest { id: 1, channel: channel.into(), url: url.into(), what: "t".into(),
            allow_hosts: allow.iter().map(|s| s.to_string()).collect(), range: None, max_bytes: None,
            headers: vec![], timeout: None, allow_loopback: false }
    }

    #[test]
    fn rules() {
        assert!(check(&req("shelf", "https://github.com/x", &["github.com"]), "https://github.com/x").is_ok());
        assert!(check(&req("shelf", "https://objects.githubusercontent.com/x", &["githubusercontent.com"]),
                      "https://objects.githubusercontent.com/x").is_ok());
        assert!(check(&req("shelf", "http://github.com/x", &["github.com"]), "http://github.com/x").is_err());
        assert!(check(&req("shelf", "https://evil.com/x", &["github.com"]), "https://evil.com/x").is_err());
        assert!(check(&req("shelf", "https://github.com.evil.com/", &["github.com"]), "https://github.com.evil.com/").is_err());
        assert!(check(&req("search", "https://192.168.1.1/", &["*"]), "https://192.168.1.1/").is_err());
        assert!(check(&req("search", "https://[::1]/", &["*"]), "https://[::1]/").is_err());
        assert!(check(&req("search", "https://router.local/", &["*"]), "https://router.local/").is_err());
        assert!(check(&req("search", "https://10.0.0.8:8443/", &["*"]), "https://10.0.0.8:8443/").is_err());
        assert!(check(&req("search", "https://example.org/", &["*"]), "https://example.org/").is_ok());
        assert!(check(&req("search", "https://user:pw@example.org/", &["*"]), "https://user:pw@example.org/").is_err());
        assert!(check(&req("messenger", "https://example.org/", &["*"]), "https://example.org/").is_err());
        assert!(check(&req("nope", "https://example.org/", &["*"]), "https://example.org/").is_err());
    }

    #[test]
    fn headers() {
        let mut r = req("search", "https://api.search.brave.com/res/v1/web/search?q=x", &["api.search.brave.com"]);
        r.headers = vec![("Accept".into(), "application/json".into()), ("X-Subscription-Token".into(), "abc".into())];
        assert!(check(&r, &r.url).is_ok());
        r.headers = vec![("Cookie".into(), "a=b".into())];
        assert_eq!(check(&r, &r.url).unwrap_err(), "header not allowed: Cookie");
        r.headers = vec![("Accept-Language".into(), "de\r\nCookie: a=b".into())];
        assert!(check(&r, &r.url).is_err());
    }

    #[test]
    fn encodings() {
        assert_eq!(base64(b""), "");
        assert_eq!(base64(b"f"), "Zg==");
        assert_eq!(base64(b"fo"), "Zm8=");
        assert_eq!(base64(b"foobar"), "Zm9vYmFy");
        assert_eq!(iso_utc(0), "1970-01-01T00:00:00+00:00");
        assert_eq!(iso_utc(1_790_000_000), "2026-09-21T14:13:20+00:00");
    }

    #[test]
    fn unknown_fields_ignored() {
        // an older server may still send "tor": the request is read and the rules decide
        let r: EgressRequest = serde_json::from_str(r#"{"channel":"messenger","url":"https://example.org/","tor":true}"#).unwrap();
        let resp = fetch(&r);
        assert!(!resp.ok && resp.error == "unknown channel: messenger");
    }
}
