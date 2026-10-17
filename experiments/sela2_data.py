"""Training data of Sela-2, built off the GPU machine (GitHub Actions: .github/workflows/sela2_data.yml).

    python -m experiments.sela2_data decon --out W/decon                 # 13-word hashes of every evaluation text
    python -m experiments.sela2_data tokenizer --work W --out data/lm2_tokenizer.json
    python -m experiments.sela2_data build --source fwe --part 0 --decon W/decon --tok T --out W/out
    python -m experiments.sela2_data chat --decon W/decon --tok T --out W/out
    python -m experiments.sela2_data val --decon W/decon --tok T --out W/out
    python -m experiments.sela2_data yardstick --decon W/decon --tok T --out W/out
    python -m experiments.sela2_data selftest                            # offline checks of the pure functions

Pretraining text (one pass, no document repeated; licences in docs/DATA_LICENSES.md):
  fwe / fwehq  HuggingFaceFW/fineweb-edu sample-10BT (ODC-By); documents with int_score ≥ 4 go to ``fwehq``
  dclm         HuggingFaceFW/dclm_100BT (CC-BY-4.0)
  cosmo        HuggingFaceTB/smollm-corpus cosmopedia-v2 (ODC-By)
  wiki_en      wikimedia/wikipedia 20231101.en (CC BY-SA 3.0), without the WikiText-103 val/test articles
  pg19         emozilla/pg19 (Project Gutenberg books before 1919, Apache-2.0 as deepmind/pg19)
  fw2_de       epfml/FineWeb2-HQ deu_Latn (ODC-By)
  wiki_de      wikimedia/wikipedia 20231101.de (CC BY-SA 3.0)
Chat and grounded question answering (``chat``): HuggingFaceTB/smoltalk2 SFT (no_think subsets, Apache-2.0; the
smol-magpie-ultra prompts and answers come from Llama-3.1-405B-Instruct, see the model card), OpenAssistant/oasst2
(Apache-2.0), databricks-dolly-15k (CC BY-SA 3.0), rajpurkar/squad_v2 (CC BY-SA 4.0), hotpotqa distractor
(CC BY-SA 4.0), DiscoResearch/germanrag (CC BY-SA 4.0), and our own identity conversations. Every conversation is
rendered with engramm/lm/chat_format.py and split by a hash of its text: 60 % for the decay phase of pretraining,
35 % for fine-tuning, 5 % held out.

Decontamination: every 13-word window (lower-cased ``\\w+`` words) of the evaluation texts — HellaSwag val, PIQA
val, ARC-Easy/Challenge test, LAMBADA test, WinoGrande dev, OpenBookQA test, MMLU test, SQuAD v2 dev, HotpotQA dev,
XQuAD-de, IFEval, and the val/test documents of the LM study (C4 + WikiText-103, the yardstick of Sela-1) — is
hashed; a training document or conversation with ≥ 3 distinct such windows is dropped and counted.

Output per stream: ``NAME.u16`` (each document as <|eos|> + its tokens), ``NAME.json`` (tokens, documents, SHA-256,
tokenizer SHA-256, what was dropped); chat streams also ``NAME.mask`` (np.packbits of the per-token fine-tuning mask).
Validation sets additionally ``NAME.starts.npy`` (position of each document's first token) and ``NAME.bytes.npy``
(UTF-8 bytes of each document's text) for bits per byte.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from engramm.lm.chat_format import (FOREIGN_IDENTITY, NO_ANSWER, SPECIAL_TOKENS, SYSTEM, SYSTEM_GROUNDED, Message,
                                    render, sources_block)

REPO = Path(__file__).resolve().parents[1]
HF = "https://huggingface.co"
VOCAB = 49_152
CTX = 2048
NGRAM = 13
MIN_HITS = 3
WORD = re.compile(r"\w+")

SOURCES = {
    #          repo                             listing prefix          regex on the file name        lang  text column(s)
    "fwe":     ("HuggingFaceFW/fineweb-edu",    "sample/10BT",          r"\d{3}_\d{5}\.parquet$",      "en"),
    "dclm":    ("HuggingFaceFW/dclm_100BT",     "data",                 r"\d{3}_\d{5}\.parquet$",      "en"),
    "cosmo":   ("HuggingFaceTB/smollm-corpus",  "cosmopedia-v2",        r"train-\d{5}-of-\d{5}\.parquet$", "en"),
    "wiki_en": ("wikimedia/wikipedia",          "20231101.en",          r"train-\d{5}-of-\d{5}\.parquet$", "en"),
    "pg19":    ("emozilla/pg19",                "data",                 r"train-\d{5}-of-\d{5}-\w+\.parquet$", "en"),
    "fw2_de":  ("epfml/FineWeb2-HQ",            "deu_Latn",             r"\d{3}_\d{5}\.parquet$",      "de"),
    "wiki_de": ("wikimedia/wikipedia",          "20231101.de",          r"train-\d{5}-of-\d{5}\.parquet$", "de"),
}
# held-out files for the validation sets (never a training part)
VAL_PART = {"fwe": 13, "dclm": 99, "cosmo": 103, "wiki_en": 40, "pg19": 22, "fw2_de": 569, "wiki_de": 19}
MIN_CHARS = 200


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# downloads
# ---------------------------------------------------------------------------

def _get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "engramm-sela2-data/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def hf_files(repo: str, prefix: str, pattern: str) -> list[tuple[str, int]]:
    """(path, size) of the files under ``prefix`` whose name matches ``pattern``, sorted by path."""
    for attempt in range(6):
        try:
            items = json.loads(_get(f"{HF}/api/datasets/{repo}/tree/main/{prefix}"))
            break
        except Exception as e:                                 # rate limits and timeouts: wait and retry
            if attempt == 5:
                raise
            log(f"listing {repo}/{prefix} failed ({e}); retry")
            time.sleep(10 * 2 ** attempt)
    rx = re.compile(pattern)
    out = sorted((x["path"], int(x.get("size", 0))) for x in items
                 if x.get("type") == "file" and rx.search(x["path"].split("/")[-1]))
    if not out:
        raise SystemExit(f"no files matching {pattern} under {repo}/{prefix}")
    return out


def download(url: str, dest: Path, size: int = 0, tries: int = 8) -> Path:
    """curl with retries and resume; accepted only with the expected size (when known)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and size and dest.stat().st_size == size:
        return dest
    for attempt in range(tries):
        rc = subprocess.call(["curl", "-fsSL", "--retry", "5", "--retry-delay", "10", "-C", "-", "-o", str(dest), url])
        if rc == 0 and (not size or dest.stat().st_size == size):
            return dest
        if rc == 33 or (size and dest.exists() and dest.stat().st_size > size):   # resume refused / too long
            dest.unlink(missing_ok=True)
        log(f"download {url} attempt {attempt + 1} failed (curl {rc}); retry")
        time.sleep(min(300, 15 * 2 ** attempt))
    raise SystemExit(f"download failed: {url}")


def source_file(source: str, part: int, work: Path) -> tuple[Path, str]:
    repo, prefix, pattern, _ = SOURCES[source]
    files = hf_files(repo, prefix, pattern)
    if part >= len(files):
        raise SystemExit(f"{source}: part {part} does not exist ({len(files)} files)")
    path, size = files[part]
    url = f"{HF}/datasets/{repo}/resolve/main/{path}"
    return download(url, work / "dl" / source / Path(path).name, size), url


def parquet_rows(path: Path, columns: list[str], batch: int = 2048):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    have = set(pf.schema_arrow.names)
    cols = [c for c in columns if c in have]
    for rb in pf.iter_batches(batch_size=batch, columns=cols):
        d = rb.to_pydict()
        n = rb.num_rows
        for i in range(n):
            yield {c: d[c][i] for c in cols}


# ---------------------------------------------------------------------------
# 13-word window hashes (decontamination)
# ---------------------------------------------------------------------------

_P = np.uint64(0x9E3779B97F4A7C15)


def word_hashes(text: str) -> np.ndarray:
    """Deterministic 64-bit hash of every lower-cased word (CRC-32 and Adler-32 of its UTF-8 bytes, the same on
    every machine and Python version)."""
    words = WORD.findall(text.lower())
    if not words:
        return np.zeros(0, dtype=np.uint64)
    enc = [w.encode("utf-8") for w in words]
    hi = np.fromiter((zlib.crc32(b) for b in enc), dtype=np.uint64, count=len(enc))
    lo = np.fromiter((zlib.adler32(b) for b in enc), dtype=np.uint64, count=len(enc))
    return (hi << np.uint64(32)) | lo


def ngram_hashes(wh: np.ndarray, n: int = NGRAM) -> np.ndarray:
    """Polynomial hash (mod 2^64) of every window of ``n`` consecutive word hashes."""
    m = len(wh) - n + 1
    if m <= 0:
        return np.zeros(0, dtype=np.uint64)
    h = np.zeros(m, dtype=np.uint64)
    with np.errstate(over="ignore"):
        for j in range(n):
            h = h * _P + wh[j:j + m]
    return h


def text_ngrams(text: str) -> np.ndarray:
    return ngram_hashes(word_hashes(text))


_DECON: np.ndarray | None = None


def _load_decon(path: str) -> None:
    global _DECON
    _DECON = np.load(path)


def hits(text: str, table: np.ndarray | None = None) -> int:
    """Distinct evaluation windows found in ``text``."""
    t = _DECON if table is None else table
    if t is None or len(t) == 0:
        return 0
    g = np.unique(text_ngrams(text))
    if not len(g):
        return 0
    pos = np.searchsorted(t, g)
    pos[pos >= len(t)] = len(t) - 1
    return int((t[pos] == g).sum())


def _hits_batch(texts: list[str]) -> list[int]:
    return [hits(x) for x in texts]


def contaminated(texts: list[str], pool: Pool | None) -> list[bool]:
    if pool is None:
        res = _hits_batch(texts)
    else:
        step = max(1, len(texts) // 64)
        res = [h for part in pool.map(_hits_batch, [texts[i:i + step] for i in range(0, len(texts), step)])
               for h in part]
    return [h >= MIN_HITS for h in res]


# ---------------------------------------------------------------------------
# evaluation texts
# ---------------------------------------------------------------------------

def hf_parquet(repo: str, config: str, split: str, work: Path) -> list[Path]:
    """The Hub's parquet export of a (small) dataset split, downloaded."""
    urls = json.loads(_get(f"{HF}/api/datasets/{repo}/parquet/{config}/{split}"))
    if not isinstance(urls, list) or not urls:
        raise SystemExit(f"no parquet export for {repo} {config} {split}: {urls}")
    d = work / "dl" / "eval" / f"{repo.replace('/', '_')}_{config}_{split}"
    return [download(u, d / f"{i}.parquet") for i, u in enumerate(urls)]


def hf_rows(repo: str, config: str, split: str, cols: list[str], work: Path):
    for f in hf_parquet(repo, config, split, work):
        yield from parquet_rows(f, cols)


def eval_texts(work: Path) -> dict[str, list[str]]:
    """Every evaluation text (benchmarks and QA test sets), by set."""
    out: dict[str, list[str]] = {}

    def rows(repo, config, split, cols):
        return hf_rows(repo, config, split, cols, work)

    out["hellaswag"] = [r["ctx"] + " " + " ".join(r["endings"]) for r in
                        rows("Rowan/hellaswag", "default", "validation", ["ctx", "endings"])]
    for name, cfg in (("arc_easy", "ARC-Easy"), ("arc_challenge", "ARC-Challenge")):
        out[name] = [r["question"] + " " + " ".join(r["choices"]["text"]) for r in
                     rows("allenai/ai2_arc", cfg, "test", ["question", "choices"])]
    out["lambada"] = [r["text"] for r in rows("EleutherAI/lambada_openai", "en", "test", ["text"])]
    out["winogrande"] = [r["sentence"] + " " + r["option1"] + " " + r["option2"] for r in
                         rows("allenai/winogrande", "winogrande_debiased", "validation", ["sentence", "option1", "option2"])]
    out["openbookqa"] = [r["question_stem"] + " " + " ".join(r["choices"]["text"]) for r in
                         rows("allenai/openbookqa", "main", "test", ["question_stem", "choices"])]
    out["mmlu"] = [r["question"] + " " + " ".join(r["choices"]) for r in rows("cais/mmlu", "all", "test", ["question", "choices"])]
    sq = list(rows("rajpurkar/squad_v2", "squad_v2", "validation", ["context", "question"]))
    out["squad_v2_dev"] = list({r["context"] for r in sq}) + [r["question"] for r in sq]
    hp = list(rows("hotpotqa/hotpot_qa", "distractor", "validation", ["question", "context"]))
    out["hotpotqa_dev"] = [r["question"] for r in hp] + list({" ".join(s) for r in hp for s in r["context"]["sentences"]})
    xq = list(rows("google/xquad", "xquad.de", "validation", ["context", "question"]))
    out["xquad_de"] = list({r["context"] for r in xq}) + [r["question"] for r in xq]
    out["ifeval"] = [r["prompt"] for r in rows("google/IFEval", "default", "train", ["prompt"])]
    out["piqa"] = _piqa(work)
    return out


def _piqa(work: Path) -> list[str]:
    base = "https://yonatanbisk.com/piqa/data"
    f = download(f"{base}/valid.jsonl", work / "dl" / "eval" / "piqa_valid.jsonl")
    return [(lambda r: r["goal"] + " " + r["sol1"] + " " + r["sol2"])(json.loads(x))
            for x in f.read_text(encoding="utf-8").splitlines() if x.strip()]


def lm_study_docs() -> dict[str, list[str]]:
    """The val-A and test documents of the LM study as text (decoded from the pinned token files; byte-level BPE
    is lossless). Needs data/cache/lm/tokens (``python -m experiments.h100_data base``)."""
    from engramm.lm.tokenizer import LMTokenizer
    tok = LMTokenizer()
    base = REPO / "data" / "cache" / "lm" / "tokens"
    out = {}
    for split in ("val_a", "test"):
        toks = np.fromfile(base / f"{split}.u16", dtype=np.uint16)
        starts = np.load(base / f"{split}.starts.npy").astype(np.int64)
        ends = np.append(starts[1:] - 1, len(toks))
        out[split] = [tok.decode(toks[s:e]) for s, e in zip(starts, ends)]
    return out


def wikitext_titles() -> set[str]:
    """Titles of the WikiText-103 articles in the LM study's val/test documents (' = Title = ' first lines)."""
    titles = set()
    for split, docs in lm_study_docs().items():
        for d in docs:
            m = re.match(r"\s*= ([^=\n]+?) =\s*\n", d)
            if m:
                titles.add(m.group(1).strip())
    return titles


def cmd_decon(args) -> None:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    work = Path(args.work)
    sets = eval_texts(work)
    lm = lm_study_docs()
    sets["lm_val_a"], sets["lm_test"] = lm["val_a"], lm["test"]
    hs, report = [], {}
    for name, texts in sets.items():
        h = [text_ngrams(t) for t in texts]
        n = int(sum(len(x) for x in h))
        report[name] = {"texts": len(texts), "windows": n}
        hs.extend(h)
        log(f"decon {name}: {len(texts)} texts, {n} windows")
    table = np.unique(np.concatenate(hs)) if hs else np.zeros(0, dtype=np.uint64)
    np.save(out / "decon_hashes.npy", table)
    titles = sorted(wikitext_titles())
    (out / "wikitext_titles.json").write_text(json.dumps(titles, ensure_ascii=False))
    report["_unique_windows"] = int(len(table))
    report["_wikitext_titles"] = len(titles)
    (out / "decon_report.json").write_text(json.dumps(report, indent=1) + "\n")
    with gzip.open(out / "lm_study_docs.json.gz", "wt", encoding="utf-8") as f:
        json.dump(lm, f, ensure_ascii=False)
    log(f"decon table: {len(table)} unique windows, {len(titles)} WikiText titles")


# ---------------------------------------------------------------------------
# tokenizer
# ---------------------------------------------------------------------------

TOK_MIX = {"fwe": 0.28, "dclm": 0.20, "cosmo": 0.10, "wiki_en": 0.10, "pg19": 0.05, "chat_en": 0.12,
           "fw2_de": 0.09, "wiki_de": 0.03, "chat_de": 0.03}


def train_bpe(texts, vocab: int = VOCAB):
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tok.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(vocab_size=vocab, min_frequency=2, show_progress=False, special_tokens=SPECIAL_TOKENS,
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet(), max_token_length=32)
    tok.train_from_iterator(texts, trainer=trainer)
    for i, s in enumerate(SPECIAL_TOKENS):
        if tok.token_to_id(s) != i:
            raise RuntimeError(f"special token {s} did not get id {i}")
    if tok.get_vocab_size() != vocab:
        raise RuntimeError(f"vocabulary has {tok.get_vocab_size()} entries, expected {vocab}")
    return tok


def _chat_texts(lang: str, work: Path, limit_chars: int) -> list[str]:
    out, n = [], 0
    for conv, lg, _src in iter_smoltalk(work, only_lang=lang):
        t = "\n".join(m.text for m in conv)
        out.append(t)
        n += len(t)
        if n >= limit_chars:
            break
    return out


def cmd_tokenizer(args) -> None:
    work = Path(args.work)
    total = int(args.chars)
    sample: dict[str, list[str]] = {}
    for name, share in TOK_MIX.items():
        want = int(total * share)
        if name.startswith("chat_"):
            sample[name] = _chat_texts(name[5:], work, want)
        else:
            part = VAL_PART[name] - 1                     # a file that is neither a training part nor validation
            path, _ = source_file(name, part, work)
            texts, n = [], 0
            for r in parquet_rows(path, ["text"]):
                t = r["text"] or ""
                if len(t) < MIN_CHARS:
                    continue
                t = t[:20_000]                            # books: many short pieces rather than a few long ones
                texts.append(t)
                n += len(t)
                if n >= want:
                    break
            sample[name] = texts
            path.unlink(missing_ok=True)
        log(f"tokenizer sample {name}: {sum(map(len, sample[name])) / 1e6:.1f} M characters")
    rng = random.Random(0)
    held = {k: v[-200:] for k, v in sample.items()}
    train = [t for k, v in sample.items() for t in v[:-200]]
    rng.shuffle(train)
    tok = train_bpe(train)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tok.save(str(out))
    from engramm.lm.tokenizer import LMTokenizer, file_sha256
    t = LMTokenizer(out, sha256=None)
    rep = {"vocab": t.vocab_size, "sha256": file_sha256(out), "chars": total, "mix": TOK_MIX, "bytes_per_token": {}}
    for k, v in held.items():
        b = sum(len(x.encode("utf-8")) for x in v)
        n = sum(len(t.encode(x)) for x in v)
        rep["bytes_per_token"][k] = round(b / max(1, n), 3)
        assert all(t.decode(t.encode(x)) == x for x in v[:50]), f"round trip failed on {k}"
    out.with_suffix(".report.json").write_text(json.dumps(rep, indent=1) + "\n")
    log(f"tokenizer {out}: {json.dumps(rep['bytes_per_token'])}")


def load_tok(path: str):
    from engramm.lm.tokenizer import LMTokenizer
    t = LMTokenizer(Path(path), sha256=None)
    if t.vocab_size != VOCAB:
        raise SystemExit(f"{path}: {t.vocab_size} tokens, expected {VOCAB}")
    for i, s in enumerate(SPECIAL_TOKENS):
        if t._tok.token_to_id(s) != i:
            raise SystemExit(f"{path}: special token {s} is not id {i}")
    return t


# ---------------------------------------------------------------------------
# writing streams
# ---------------------------------------------------------------------------

def write_stream(out: Path, name: str, docs: list[np.ndarray], tok_sha: str, extra: dict,
                 masks: list[np.ndarray] | None = None, nbytes: list[int] | None = None) -> dict:
    """docs: token arrays that already start with <|eos|>. Writes NAME.u16 (+ .mask, .starts.npy, .bytes.npy)."""
    out.mkdir(parents=True, exist_ok=True)
    total = int(sum(len(d) for d in docs))
    arr = np.empty(total, dtype=np.uint16)
    starts = np.empty(len(docs), dtype=np.int64)
    p = 0
    for i, d in enumerate(docs):
        if len(d) == 0 or d[0] != 0:
            raise ValueError("every document must start with <|eos|>")
        arr[p:p + len(d)] = d
        starts[i] = p + 1
        p += len(d)
    path = out / f"{name}.u16"
    arr.tofile(path)
    rec = {"name": name, "tokens": total, "docs": len(docs), "sha256": sha256_file(path), "tokenizer_sha256": tok_sha,
           **extra}
    if masks is not None:
        m = np.concatenate(masks).astype(np.uint8) if masks else np.zeros(0, dtype=np.uint8)
        if len(m) != total:
            raise ValueError("mask length differs from the tokens")
        np.packbits(m).tofile(out / f"{name}.mask")
        rec["mask_tokens"] = int(m.sum())
        rec["mask_sha256"] = sha256_file(out / f"{name}.mask")
    if nbytes is not None:
        np.save(out / f"{name}.starts.npy", starts)
        np.save(out / f"{name}.bytes.npy", np.asarray(nbytes, dtype=np.int64))
    (out / f"{name}.json").write_text(json.dumps(rec, indent=1) + "\n")
    log(f"wrote {name}: {total / 1e6:.1f} M tokens, {len(docs)} documents")
    return rec


def sha256_file(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def encode_docs(tok, texts: list[str], batch: int = 4096) -> list[np.ndarray]:
    out = []
    for i in range(0, len(texts), batch):
        for ids in tok._tok.encode_batch(texts[i:i + batch], add_special_tokens=False):
            a = np.empty(len(ids.ids) + 1, dtype=np.uint16)
            a[0] = 0
            a[1:] = ids.ids
            out.append(a)
    return out


# ---------------------------------------------------------------------------
# pretraining text
# ---------------------------------------------------------------------------

def read_source(source: str, path: Path, titles: set[str], limit_docs: int = 0) -> tuple[dict[str, list[str]], dict]:
    """Filtered texts of one file, by output stream; and counts of what was dropped."""
    cols = ["text", "title", "int_score"]
    streams: dict[str, list[str]] = {}
    drop = {"short": 0, "wikitext_title": 0}
    n = 0
    for r in parquet_rows(path, cols):
        t = (r.get("text") or "").strip()
        if len(t) < MIN_CHARS:
            drop["short"] += 1
            continue
        if source == "wiki_en" and (r.get("title") or "").strip() in titles:
            drop["wikitext_title"] += 1
            continue
        if source in ("wiki_en", "wiki_de") and r.get("title"):
            t = f"{r['title'].strip()}\n\n{t}"
        name = source
        if source == "fwe":
            name = "fwehq" if (r.get("int_score") or 0) >= 4 else "fwe"
        streams.setdefault(name, []).append(t)
        n += 1
        if limit_docs and n >= limit_docs:
            break
    return streams, drop


def cmd_build(args) -> None:
    work, out = Path(args.work), Path(args.out)
    tok = load_tok(args.tok)
    titles = set(json.loads((Path(args.decon) / "wikitext_titles.json").read_text()))
    path, url = source_file(args.source, args.part, work)
    streams, drop = read_source(args.source, path, titles, args.limit_docs)
    path.unlink(missing_ok=True)                                  # the runner's disk is small
    rng = np.random.default_rng(1000 + args.part)
    with Pool(args.workers, initializer=_load_decon, initargs=(str(Path(args.decon) / "decon_hashes.npy"),)) as pool:
        for name, texts in streams.items():
            bad = contaminated(texts, pool)
            keep = [t for t, b in zip(texts, bad) if not b]
            order = rng.permutation(len(keep))
            keep = [keep[i] for i in order]
            docs = encode_docs(tok, keep)
            write_stream(out, f"{name}_{args.part}", docs, tok_sha=sha256_file(Path(args.tok)),
                         extra={"source": args.source, "part": args.part, "url": url, "lang": SOURCES[args.source][3],
                                "dropped_contaminated": int(sum(bad)), "dropped": drop,
                                "chars": int(sum(len(t) for t in keep))})


def cmd_val(args) -> None:
    """Held-out documents of every source (files that are never training parts), for bits per byte."""
    work, out = Path(args.work), Path(args.out)
    tok = load_tok(args.tok)
    titles = set(json.loads((Path(args.decon) / "wikitext_titles.json").read_text()))
    _load_decon(str(Path(args.decon) / "decon_hashes.npy"))
    for source, part in VAL_PART.items():
        path, url = source_file(source, part, work)
        streams, _ = read_source(source, path, titles, limit_docs=args.docs * 3)
        path.unlink(missing_ok=True)
        for name, texts in streams.items():
            texts = [t for t, b in zip(texts, contaminated(texts, None)) if not b][:args.docs]
            docs = encode_docs(tok, texts)
            write_stream(out, f"val_{name}", docs, tok_sha=sha256_file(Path(args.tok)),
                         extra={"source": source, "part": part, "url": url}, nbytes=[len(t.encode("utf-8")) for t in texts])


def cmd_yardstick(args) -> None:
    """The LM study's val-A/test documents with the Sela-2 tokenizer (bits per byte comparable with GPT-2 small
    1.036 and Sela-1 0.989 on the same documents)."""
    out = Path(args.out)
    tok = load_tok(args.tok)
    with gzip.open(Path(args.decon) / "lm_study_docs.json.gz", "rt", encoding="utf-8") as f:
        lm = json.load(f)
    base = REPO / "data" / "cache" / "lm" / "tokens"
    for split, texts in lm.items():
        nb = np.load(base / f"{split}.bytes.npy").astype(np.int64) if (base / f"{split}.bytes.npy").exists() else \
            np.asarray([len(t.encode("utf-8")) for t in texts])
        docs = encode_docs(tok, texts)
        write_stream(out, f"lm_{split}", docs, tok_sha=sha256_file(Path(args.tok)), extra={"split": split},
                     nbytes=[int(x) for x in nb])


# ---------------------------------------------------------------------------
# chat and grounded question answering
# ---------------------------------------------------------------------------

DE_WORDS = set("der die das und ist nicht ich sie mit für auf ein eine zu den von sich des dem im auch es wir ihr "
               "werden wird sind oder aber wenn wie bei nach können kann dass noch nur über diese einen einem".split())
OTHER_WORDS = set("le la les et est une des pour pas que qui dans el los las por para con una que del como "
                  "il di che non per sono gli della os um uma não com para mais".split())


def is_german(text: str) -> bool:
    w = WORD.findall(text.lower()[:2000])
    if len(w) < 5:
        return False
    de = sum(x in DE_WORDS for x in w)
    other = sum(x in OTHER_WORDS for x in w)
    return de / len(w) > 0.08 and de > 2 * other


SMOLTALK_EN = ["smoltalk_smollm3_smol_magpie_ultra_no_think", "smoltalk_smollm3_everyday_conversations_no_think",
               "smoltalk_smollm3_systemchats_30k_no_think", "smoltalk_smollm3_smol_rewrite_no_think",
               "smoltalk_smollm3_smol_summarize_no_think", "smoltalk_smollm3_explore_instruct_rewriting_no_think"]
SMOLTALK_DE = ["smoltalk_multilingual_8languages_lang_5_no_think"]


def iter_smoltalk(work: Path, only_lang: str | None = None):
    """(messages, lang, subset) of the smoltalk2 SFT subsets; German only from the multilingual subset."""
    subsets = (SMOLTALK_EN if only_lang in (None, "en") else []) + (SMOLTALK_DE if only_lang in (None, "de") else [])
    for sub in subsets:
        for p, s in hf_files("HuggingFaceTB/smoltalk2", "SFT", rf"^{re.escape(sub)}-\d{{5}}-of-\d{{5}}\.parquet$"):
            f = download(f"{HF}/datasets/HuggingFaceTB/smoltalk2/resolve/main/{p}", work / "dl" / "chat" / Path(p).name, s)
            for r in parquet_rows(f, ["messages", "chat_template_kwargs"]):
                msgs = [Message(m["role"], m["content"]) for m in (r.get("messages") or [])
                        if m.get("role") in ("system", "user", "assistant") and isinstance(m.get("content"), str)]
                if not msgs:
                    continue
                kw = r.get("chat_template_kwargs") or {}
                sysmsg = (kw.get("custom_instructions") or "").strip()
                if sysmsg and msgs[0].role != "system":
                    msgs = [Message("system", sysmsg)] + msgs
                lang = "en"
                if sub in SMOLTALK_DE:
                    if not is_german(" ".join(m.text for m in msgs[:3])):
                        continue
                    lang = "de"
                yield msgs, lang, sub


def iter_oasst(work: Path):
    """Best-ranked path of every English or German OpenAssistant tree."""
    f = download(f"{HF}/datasets/OpenAssistant/oasst2/resolve/main/2023-11-05_oasst2_ready.trees.jsonl.gz",
                 work / "dl" / "chat" / "oasst2_ready.trees.jsonl.gz")
    with gzip.open(f, "rt", encoding="utf-8") as fh:
        for line in fh:
            tree = json.loads(line)
            root = tree.get("prompt") or {}
            lang = root.get("lang")
            if lang not in ("en", "de"):
                continue
            msgs, node = [], root
            while node:
                role = "user" if node.get("role") == "prompter" else "assistant"
                msgs.append(Message(role, node.get("text") or ""))
                kids = [k for k in (node.get("replies") or []) if not k.get("deleted")]
                if not kids:
                    break
                kids.sort(key=lambda k: (k.get("rank") is None, k.get("rank") if k.get("rank") is not None else 0))
                node = kids[0]
            if msgs and msgs[-1].role == "user":
                msgs = msgs[:-1]
            if len(msgs) >= 2:
                yield msgs, lang, "oasst2"


def iter_dolly(work: Path):
    f = download(f"{HF}/datasets/databricks/databricks-dolly-15k/resolve/main/databricks-dolly-15k.jsonl",
                 work / "dl" / "chat" / "dolly15k.jsonl")
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        ctx = (r.get("context") or "").strip()
        if ctx and r.get("category") in ("closed_qa", "information_extraction", "summarization"):
            ans = r["response"].strip()
            ans = ans if re.search(r"\[1\]", ans) else ans.rstrip() + " [1]"
            yield [Message("system", SYSTEM_GROUNDED["en"]), Message("sources", sources_block([("", ctx)])),
                   Message("user", r["instruction"].strip()), Message("assistant", ans)], "en", "dolly_grounded"
        elif not ctx:
            yield [Message("user", r["instruction"].strip()), Message("assistant", r["response"].strip())], "en", "dolly"


SENT = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9\"'(])")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT.split(text.strip()) if s.strip()]


def grounded_example(rng: random.Random, title: str, context: str, question: str, answers: list[str],
                     answer_start: int | None, distract: list[tuple[str, str]], lang: str = "en") -> list[Message]:
    """App-format grounded QA from a reading-comprehension item: the context's sentences (the answer sentence and
    its neighbours) as one numbered source among distractor sources; answer = the span or its sentence, cited.
    No answer in the context → the fixed abstention."""
    sents = split_sentences(context)
    ans_sent = None
    if answers and answer_start is not None:
        pos = 0
        for i, s in enumerate(sents):
            j = context.find(s, pos)
            if j < 0:
                continue
            if j <= answer_start < j + len(s) + 1:
                ans_sent = i
                break
            pos = j + len(s)
    if ans_sent is not None:
        lo, hi = max(0, ans_sent - 1), min(len(sents), ans_sent + 2)
        own = " ".join(sents[lo:hi])
    else:
        k = rng.randrange(max(1, len(sents)))
        own = " ".join(sents[k:k + 3])
    srcs = [(title, own)] + distract[:rng.randint(1, 4)]
    rng.shuffle(srcs)
    idx = srcs.index((title, own)) + 1
    if answers and ans_sent is not None and answers[0].strip():
        span = answers[0].strip().rstrip(".")
        if rng.random() < 0.5:
            reply = f"{span[0].upper() + span[1:]} [{idx}]."
        else:
            sent = sents[ans_sent]
            end = sent[-1] if sent[-1] in ".!?" else "."
            reply = f"{sent.rstrip('.!?')} [{idx}]{end}"
    else:
        reply = NO_ANSWER[lang]
    return [Message("system", SYSTEM_GROUNDED[lang]), Message("sources", sources_block(srcs)),
            Message("user", question.strip()), Message("assistant", reply)]


def iter_grounded(work: Path, rng: random.Random):
    rows = list(hf_rows("rajpurkar/squad_v2", "squad_v2", "train", ["title", "context", "question", "answers"], work))
    by_title: dict[str, list[str]] = {}
    for r in rows:
        by_title.setdefault(r["title"], []).append(r["context"])
    titles = list(by_title)
    for r in rows:
        a = r["answers"] or {}
        texts, starts = list(a.get("text") or []), list(a.get("answer_start") or [])
        distract = []
        for _ in range(4):
            t = rng.choice(titles)
            c = rng.choice(by_title[t])
            ss = split_sentences(c)
            k = rng.randrange(max(1, len(ss)))
            distract.append((t.replace("_", " "), " ".join(ss[k:k + 2])))
        yield (grounded_example(rng, r["title"].replace("_", " "), r["context"], r["question"], texts,
                                starts[0] if starts else None, distract), "en", "squad_v2")
    if True:
        for r in hf_rows("hotpotqa/hotpot_qa", "distractor", "train", ["question", "answer", "context", "supporting_facts"],
                         work):
            titles_c, sents_c = r["context"]["title"], r["context"]["sentences"]
            sup = set(r["supporting_facts"]["title"])
            srcs = [(t, " ".join(s).strip()) for t, s in zip(titles_c, sents_c)]
            rng.shuffle(srcs)
            srcs = srcs[:6]
            cites = [i + 1 for i, (t, _) in enumerate(srcs) if t in sup]
            ans = (r["answer"] or "").strip()
            if not ans:
                continue
            if cites:
                reply = f"{ans[0].upper() + ans[1:]} " + "".join(f"[{c}]" for c in cites) + "."
            else:
                reply = NO_ANSWER["en"]
            yield ([Message("system", SYSTEM_GROUNDED["en"]), Message("sources", sources_block(srcs)),
                    Message("user", r["question"].strip()), Message("assistant", reply)], "en", "hotpotqa")
    if True:
        for r in hf_rows("DiscoResearch/germanrag", "default", "train", ["contexts", "question", "answer", "positive_ctx_idx"],
                         work):
            ctxs = [c.strip() for c in (r.get("contexts") or []) if isinstance(c, str)]
            if not ctxs or not r.get("question"):
                continue
            pi = r.get("positive_ctx_idx")
            ans = (r.get("answer") or "").strip()
            if pi is None or pi < 0 or "nicht zu beantworten" in ans:
                reply = NO_ANSWER["de"]
            else:
                reply = ans.rstrip() + f" [{int(pi) + 1}]"
            yield ([Message("system", SYSTEM_GROUNDED["de"]), Message("sources", sources_block([("", c) for c in ctxs])),
                    Message("user", r["question"].strip()), Message("assistant", reply)], "de", "germanrag")


IDENTITY_Q = {
    "en": ["Who are you?", "What are you?", "What's your name?", "What is your name?", "Who made you?",
           "Who created you?", "Who trained you?", "Are you ChatGPT?", "Are you Claude?", "Are you an AI?",
           "Which model are you?", "Tell me about yourself.", "What can you do?", "Do you need the internet?",
           "Where do you run?", "Are you a person?", "How were you trained?", "Introduce yourself.",
           "Are you based on Llama or GPT?", "Can you look things up?", "Do you know everything?",
           "Is my data sent anywhere?", "who r u", "what are u"],
    "de": ["Wer bist du?", "Was bist du?", "Wie heißt du?", "Wer hat dich gemacht?", "Wer hat dich trainiert?",
           "Bist du ChatGPT?", "Bist du eine KI?", "Welches Modell bist du?", "Erzähl mir etwas über dich.",
           "Was kannst du?", "Brauchst du Internet?", "Wo läufst du?", "Bist du ein Mensch?",
           "Wie wurdest du trainiert?", "Stell dich vor.", "Basierst du auf Llama oder GPT?",
           "Weißt du alles?", "Werden meine Daten irgendwohin geschickt?", "wer bist du eigentlich"],
}
IDENTITY_A = {
    "en": ["I'm Sela, a small language model. I was trained from scratch in the ENGRAMM project on public text, so "
           "I'm not built on any other company's model. I run offline on your computer.",
           "My name is Sela. I'm a compact language model trained from scratch by the ENGRAMM project. I run "
           "locally on your device, and our conversation stays here.",
           "I'm Sela, ENGRAMM's own small language model. I can chat, explain things, rewrite and summarise text. "
           "For facts, ENGRAMM can give me sources from its knowledge pack, and I cite them. Without sources I can "
           "get facts wrong, so please double-check important details.",
           "I'm Sela, a small offline assistant trained from scratch in the ENGRAMM project. I'm not ChatGPT, "
           "Claude or Llama, and I don't need the internet to work."],
    "de": ["Ich bin Sela, ein kleines Sprachmodell. Ich wurde im ENGRAMM-Projekt von Grund auf mit öffentlichen "
           "Texten trainiert und basiere nicht auf dem Modell einer anderen Firma. Ich laufe offline auf deinem "
           "Computer.",
           "Ich heiße Sela. Ich bin ein kompaktes Sprachmodell, das im ENGRAMM-Projekt von Grund auf trainiert "
           "wurde. Ich laufe lokal auf deinem Gerät, und unser Gespräch bleibt hier.",
           "Ich bin Sela, das eigene kleine Sprachmodell von ENGRAMM. Ich kann mich unterhalten, Dinge erklären, "
           "Texte umschreiben und zusammenfassen. Für Fakten gibt mir ENGRAMM Quellen aus seinem Wissenspaket, und "
           "ich zitiere sie. Ohne Quellen kann ich mich bei Fakten irren.",
           "Ich bin Sela, ein kleiner Offline-Assistent aus dem ENGRAMM-Projekt. Ich bin weder ChatGPT noch Claude "
           "oder Llama und brauche kein Internet."],
}
GREET = {
    "en": [("hi", "Hi! How can I help you today?"), ("hello", "Hello! What can I do for you?"),
           ("Hey!", "Hey! What's on your mind?"), ("Good morning!", "Good morning! How can I help?"),
           ("How are you?", "I'm doing well, thanks for asking! How can I help you today?"),
           ("Thanks!", "You're welcome!"), ("Thank you so much", "Happy to help! Anything else?"),
           ("bye", "Goodbye! Have a great day.")],
    "de": [("hallo", "Hallo! Wie kann ich dir helfen?"), ("Hi!", "Hi! Was kann ich für dich tun?"),
           ("Guten Morgen!", "Guten Morgen! Wie kann ich helfen?"),
           ("Wie geht es dir?", "Mir geht es gut, danke der Nachfrage! Wie kann ich dir helfen?"),
           ("Danke!", "Gern geschehen!"), ("Vielen Dank", "Sehr gern! Kann ich sonst noch etwas tun?"),
           ("tschüss", "Tschüss! Einen schönen Tag noch.")],
}


def iter_identity(rng: random.Random, n: int = 2000):
    for i in range(n):
        lang = "de" if i % 3 == 2 else "en"
        msgs = []
        if rng.random() < 0.5:
            msgs.append(Message("system", SYSTEM[lang]))
        if rng.random() < 0.4:
            g, a = rng.choice(GREET[lang])
            msgs += [Message("user", g), Message("assistant", a)]
        msgs += [Message("user", rng.choice(IDENTITY_Q[lang])), Message("assistant", rng.choice(IDENTITY_A[lang]))]
        if rng.random() < 0.3:
            g, a = rng.choice(GREET[lang][-3:])
            msgs += [Message("user", g), Message("assistant", a)]
        yield msgs, lang, "identity"


def bucket(msgs: list[Message]) -> str:
    h = int(hashlib.md5("\x1e".join(m.text for m in msgs).encode("utf-8")).hexdigest()[:8], 16) % 100
    return "decay" if h < 60 else "sft" if h < 95 else "val"


def prepare(msgs: list[Message], lang: str, rng: random.Random) -> list[Message] | None:
    if not msgs or msgs[-1].role != "assistant" or not any(m.role == "user" for m in msgs):
        return None
    if any(m.role == "assistant" and FOREIGN_IDENTITY.search(m.text) for m in msgs):
        return None
    if any(not m.text.strip() for m in msgs):
        return None
    if msgs[0].role != "system" and rng.random() < 0.5:
        msgs = [Message("system", SYSTEM[lang])] + msgs
    return msgs


def cmd_chat(args) -> None:
    work, out = Path(args.work), Path(args.out)
    tok = load_tok(args.tok)
    tok_sha = sha256_file(Path(args.tok))
    _load_decon(str(Path(args.decon) / "decon_hashes.npy"))
    rng = random.Random(7)
    groups: dict[str, dict[str, tuple[list, list]]] = {}
    counts: dict[str, dict[str, int]] = {}

    def add(stream: str, msgs, lang, src):
        c = counts.setdefault(src, {"in": 0, "kept": 0, "foreign_or_bad": 0, "too_long": 0, "contaminated": 0})
        c["in"] += 1
        p = prepare(msgs, lang, rng) if src not in ("identity",) else msgs
        if p is None:
            c["foreign_or_bad"] += 1
            return
        if src not in ("identity",) and hits("\n".join(m.text for m in p)) >= MIN_HITS:
            c["contaminated"] += 1
            return
        try:
            ids, mask = render(tok, p, max_tokens=CTX)
        except ValueError:
            c["too_long"] += 1
            return
        c["kept"] += 1
        b = bucket(p)
        d = groups.setdefault(f"{stream}_{b}", {})
        d.setdefault("ids", []).append(np.asarray(ids, dtype=np.uint16))
        d.setdefault("mask", []).append(np.asarray(mask, dtype=np.uint8))

    def limited(it):                       # --limit: at most that many conversations per source (tests)
        seen: dict[str, int] = {}
        for item in it:
            seen[item[2]] = seen.get(item[2], 0) + 1
            if not args.limit or seen[item[2]] <= args.limit:
                yield item

    for msgs, lang, src in limited(iter_smoltalk(work)):
        add("chat_" + lang, msgs, lang, src)
    for msgs, lang, src in limited(iter_oasst(work)):
        add("chat_" + lang, msgs, lang, src)
    for msgs, lang, src in limited(iter_dolly(work)):
        add("grounded" if src.endswith("grounded") else "chat_en", msgs, lang, src)
    for msgs, lang, src in limited(iter_grounded(work, rng)):
        add("grounded", msgs, lang, src)
    ident = list(iter_identity(rng))
    for msgs, lang, src in ident:
        add("identity", msgs, lang, src)
    for name, d in sorted(groups.items()):
        order = list(range(len(d["ids"])))
        rng.shuffle(order)
        write_stream(out, name, [d["ids"][i] for i in order], tok_sha, extra={"kind": "chat"},
                     masks=[d["mask"][i] for i in order])
    (out / "chat_counts.json").write_text(json.dumps(counts, indent=1) + "\n")
    log(json.dumps(counts))


# ---------------------------------------------------------------------------
# offline self-test (no network): hashing, decontamination, chat rendering, grounded examples
# ---------------------------------------------------------------------------

def cmd_selftest(args) -> None:
    a = text_ngrams("The quick brown fox jumps over the lazy dog while the cat sleeps on the warm mat today.")
    b = text_ngrams("THE quick, brown fox jumps over the lazy dog -- while the cat sleeps on the warm mat today!")
    assert len(a) == 6 and np.array_equal(a, b), "window hashes must ignore case and punctuation"
    table = np.unique(a)
    assert hits("noise " * 5 + "the quick brown fox jumps over the lazy dog while the cat sleeps on the warm mat "
                "today and more", table) >= MIN_HITS
    assert hits("an unrelated sentence about the history of rome and its many emperors over the centuries", table) == 0
    assert is_german("Ich glaube, dass das nicht so einfach ist, aber wir können es versuchen.")
    assert not is_german("Je pense que ce n'est pas si simple, mais nous pouvons essayer pour une fois.")
    assert not is_german("I think that this is not so simple, but we can try it once more today.")
    rng = random.Random(0)
    ex = grounded_example(rng, "Normandy", "The Normans were the people who gave their name to Normandy. They "
                          "descended from Norse raiders. Their identity emerged in the 10th century.",
                          "Who gave their name to Normandy?", ["The Normans"], 0,
                          [("Paris", "Paris is the capital of France."), ("Rome", "Rome is in Italy.")])
    assert ex[1].role == "sources" and ex[-1].role == "assistant" and re.search(r"\[\d\]", ex[-1].text)
    none = grounded_example(rng, "X", "Some text here. More text.", "What?", [], None, [("Y", "Other.")])
    assert none[-1].text == NO_ANSWER["en"]
    assert bucket([Message("user", "a"), Message("assistant", "b")]) in ("decay", "sft", "val")
    assert prepare([Message("user", "Who are you?"), Message("assistant", "I am ChatGPT.")], "en", rng) is None
    print("selftest ok")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("decon")
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="/tmp/sela2_work")
    p.set_defaults(func=cmd_decon)
    p = sub.add_parser("tokenizer")
    p.add_argument("--out", required=True)
    p.add_argument("--work", default="/tmp/sela2_work")
    p.add_argument("--chars", type=float, default=8e8)
    p.set_defaults(func=cmd_tokenizer)
    for name, fn in (("build", cmd_build), ("chat", cmd_chat), ("val", cmd_val), ("yardstick", cmd_yardstick)):
        p = sub.add_parser(name)
        p.add_argument("--tok", required=True)
        p.add_argument("--decon", required=True)
        p.add_argument("--out", required=True)
        p.add_argument("--work", default="/tmp/sela2_work")
        p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2)))
        if name == "build":
            p.add_argument("--source", required=True, choices=sorted(SOURCES))
            p.add_argument("--part", type=int, required=True)
            p.add_argument("--limit-docs", type=int, default=0)
        if name == "val":
            p.add_argument("--docs", type=int, default=2000)
        if name == "chat":
            p.add_argument("--limit", type=int, default=0)
        p.set_defaults(func=fn)
    p = sub.add_parser("selftest")
    p.set_defaults(func=cmd_selftest)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
