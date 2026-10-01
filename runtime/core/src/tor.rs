//! Fetching a page over Tor (feature `tor`): an embedded Arti client, TLS with rustls and the
//! Mozilla root store (webpki-roots), and a minimal HTTP/1.1 GET (Connection: close, chunked
//! decoding, size limit). Used only by the messenger channel (docs/SPEC_ATLAS.md, K3): the
//! target site sees a Tor exit, never the user's address or a search term.

use arti_client::config::CfgPath;
use arti_client::{TorClient, TorClientConfig};
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio_rustls::rustls::{ClientConfig, RootCertStore};
use tokio_rustls::rustls::pki_types::ServerName;
use tokio_rustls::TlsConnector;
use tor_rtcompat::PreferredRuntime;

pub struct TorFetcher {
    rt: tokio::runtime::Runtime,
    client: Arc<TorClient<PreferredRuntime>>,
    tls: TlsConnector,
}

pub struct HttpResponse {
    pub status: u16,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}

impl HttpResponse {
    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers.iter().find(|(k, _)| k.eq_ignore_ascii_case(name)).map(|(_, v)| v.as_str())
    }
}

impl TorFetcher {
    /// Start Arti with its state and cache under `dir` and bootstrap a connection to the Tor
    /// network (the first start downloads the directory: tens of seconds).
    pub fn start(dir: &Path) -> Result<Self, String> {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .worker_threads(2)
            .enable_all()
            .build()
            .map_err(|e| format!("tokio: {e}"))?;
        let mut builder = TorClientConfig::builder();
        builder
            .storage()
            .state_dir(CfgPath::new_literal(dir.join("state")))
            .cache_dir(CfgPath::new_literal(dir.join("cache")));
        let config = builder.build().map_err(|e| format!("tor config: {e}"))?;
        let client = rt
            .block_on(async { tokio::time::timeout(Duration::from_secs(180), TorClient::create_bootstrapped(config)).await })
            .map_err(|_| "tor bootstrap timed out".to_string())?
            .map_err(|e| format!("tor bootstrap failed: {e}"))?;
        let roots = RootCertStore { roots: webpki_roots::TLS_SERVER_ROOTS.to_vec() };
        let tls_config = ClientConfig::builder_with_provider(Arc::new(tokio_rustls::rustls::crypto::ring::default_provider()))
            .with_safe_default_protocol_versions()
            .map_err(|e| format!("tls: {e}"))?
            .with_root_certificates(roots)
            .with_no_client_auth();
        Ok(TorFetcher { rt, client, tls: TlsConnector::from(Arc::new(tls_config)) })
    }

    /// One HTTPS GET over a fresh Tor stream.
    pub fn get(&self, host: &str, port: u16, path: &str, range: Option<(u64, u64)>, limit: u64, timeout: f64,
               user_agent: &str) -> Result<HttpResponse, String> {
        let fut = async {
            let stream = self.client.connect((host, port)).await.map_err(|e| format!("tor connect: {e}"))?;
            let name = ServerName::try_from(host.to_string()).map_err(|e| format!("bad host name: {e}"))?;
            let mut tls = self.tls.connect(name, stream).await.map_err(|e| format!("tls: {e}"))?;
            let mut req = format!(
                "GET {path} HTTP/1.1\r\nHost: {host}\r\nUser-Agent: {user_agent}\r\nAccept: */*\r\n\
                 Accept-Encoding: identity\r\nConnection: close\r\n"
            );
            if let Some((a, b)) = range {
                req.push_str(&format!("Range: bytes={a}-{b}\r\n"));
            }
            req.push_str("\r\n");
            tls.write_all(req.as_bytes()).await.map_err(|e| format!("write: {e}"))?;
            let mut raw = Vec::new();
            let cap = limit + 64 * 1024;
            let mut buf = vec![0u8; 16 * 1024];
            loop {
                let n = match tls.read(&mut buf).await {
                    Ok(0) => break,
                    Ok(n) => n,
                    // servers that close without a TLS close_notify: the body is complete when
                    // Content-Length says so; parse_response checks it
                    Err(e) if e.kind() == std::io::ErrorKind::UnexpectedEof => break,
                    Err(e) => return Err(format!("read: {e}")),
                };
                raw.extend_from_slice(&buf[..n]);
                if raw.len() as u64 > cap {
                    return Err(format!("response larger than {limit} bytes"));
                }
            }
            parse_response(&raw, limit)
        };
        self.rt
            .block_on(async { tokio::time::timeout(Duration::from_secs_f64(timeout.clamp(5.0, 180.0)), fut).await })
            .map_err(|_| "tor request timed out".to_string())?
    }
}

/// Status line, headers and body of a raw HTTP/1.1 response (chunked bodies decoded).
pub fn parse_response(raw: &[u8], limit: u64) -> Result<HttpResponse, String> {
    let end = raw.windows(4).position(|w| w == b"\r\n\r\n").ok_or("no HTTP header")?;
    let head = std::str::from_utf8(&raw[..end]).map_err(|_| "header is not text")?;
    let mut lines = head.split("\r\n");
    let status_line = lines.next().unwrap_or("");
    let status: u16 = status_line.split_whitespace().nth(1).and_then(|s| s.parse().ok()).ok_or("bad status line")?;
    let headers: Vec<(String, String)> = lines
        .filter_map(|l| l.split_once(':').map(|(k, v)| (k.trim().to_string(), v.trim().to_string())))
        .collect();
    let mut body = raw[end + 4..].to_vec();
    let chunked = headers.iter().any(|(k, v)| k.eq_ignore_ascii_case("transfer-encoding") && v.to_ascii_lowercase().contains("chunked"));
    if chunked {
        body = dechunk(&body)?;
    } else if let Some(len) = headers.iter().find(|(k, _)| k.eq_ignore_ascii_case("content-length")).and_then(|(_, v)| v.parse::<usize>().ok()) {
        if body.len() < len {
            return Err("connection closed before the whole body arrived".into());
        }
        body.truncate(len);
    }
    if body.len() as u64 > limit {
        return Err(format!("response larger than {limit} bytes"));
    }
    Ok(HttpResponse { status, headers, body })
}

fn dechunk(mut data: &[u8]) -> Result<Vec<u8>, String> {
    let mut out = Vec::new();
    loop {
        let line_end = data.windows(2).position(|w| w == b"\r\n").ok_or("bad chunk")?;
        let size_txt = std::str::from_utf8(&data[..line_end]).map_err(|_| "bad chunk size")?;
        let size = usize::from_str_radix(size_txt.split(';').next().unwrap_or("").trim(), 16).map_err(|_| "bad chunk size")?;
        data = &data[line_end + 2..];
        if size == 0 {
            return Ok(out);
        }
        if data.len() < size + 2 {
            return Err("truncated chunk".into());
        }
        out.extend_from_slice(&data[..size]);
        data = &data[size + 2..];
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_plain_and_chunked() {
        let r = parse_response(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\nContent-Type: text/html\r\n\r\nhello", 100).unwrap();
        assert_eq!((r.status, r.body.as_slice(), r.header("content-type")), (200, &b"hello"[..], Some("text/html")));
        let r = parse_response(b"HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n", 100)
            .unwrap();
        assert_eq!(r.body, b"hello world");
        assert!(parse_response(b"HTTP/1.1 200 OK\r\nContent-Length: 50\r\n\r\nshort", 100).is_err());
        assert!(parse_response(b"HTTP/1.1 200 OK\r\nContent-Length: 5\r\n\r\nhello", 3).is_err());
        let r = parse_response(b"HTTP/1.1 302 Found\r\nLocation: https://x.org/a\r\n\r\n", 100).unwrap();
        assert_eq!((r.status, r.header("location")), (302, Some("https://x.org/a")));
    }
}
