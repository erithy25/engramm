"""Byte-level BPE tokenizer for ENGRAMM-LM (docs/PREREG_LM.md §4).

The vocabulary is learnt by counting adjacent pairs (``tokenizers`` BPE
trainer) — no model is involved. Byte-level means every string is
representable and ``decode(encode(x)) == x`` holds exactly. Token 0 is
``<|eos|>``, the end-of-document marker; it also opens every context.

The trained file is committed (``data/lm_tokenizer.json``) and pinned by
SHA-256, so every later step sees the identical vocabulary.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Sequence
from pathlib import Path

import numpy as np

EOS = 0
EOS_TEXT = "<|eos|>"
VOCAB_SIZE = 32_768
DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "lm_tokenizer.json"
#: SHA-256 of the committed tokenizer file; checked on every load.
TOKENIZER_SHA256 = "637745134e61a6278b47667b3e1bc1fde418c314753ab8598773a6a27fca513d"


def _new_tokenizer():
    from tokenizers import Tokenizer, decoders, models, pre_tokenizers

    tok = Tokenizer(models.BPE())
    tok.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False, use_regex=True)
    tok.decoder = decoders.ByteLevel()
    return tok


def train_tokenizer(texts: Iterable[str], vocab_size: int = VOCAB_SIZE):
    """Learn a byte-level BPE vocabulary of ``vocab_size`` tokens by pair counting."""
    from tokenizers import pre_tokenizers, trainers

    tok = _new_tokenizer()
    trainer = trainers.BpeTrainer(vocab_size=vocab_size, min_frequency=2, show_progress=False,
                                  special_tokens=[EOS_TEXT],
                                  initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
                                  max_token_length=32)
    tok.train_from_iterator(texts, trainer=trainer)
    if tok.token_to_id(EOS_TEXT) != EOS:
        raise RuntimeError("<|eos|> did not receive id 0")
    if tok.get_vocab_size() > vocab_size:
        raise RuntimeError(f"vocabulary has {tok.get_vocab_size()} > {vocab_size} entries")
    return tok


def file_sha256(path: Path | str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LMTokenizer:
    """Thin, checked wrapper: text <-> uint16 token ids."""

    def __init__(self, path: Path | str = DEFAULT_PATH, sha256: str | None = TOKENIZER_SHA256) -> None:
        from tokenizers import Tokenizer

        self.path = Path(path)
        self.sha256 = file_sha256(self.path)
        if sha256 is not None and self.sha256 != sha256:
            raise RuntimeError(f"tokenizer {self.path} has SHA-256 {self.sha256}, expected {sha256}")
        self._tok = Tokenizer.from_file(str(self.path))
        # the literal text "<|eos|>" is ordinary text; only id 0 ends a document
        self._tok.encode_special_tokens = True
        self.vocab_size = self._tok.get_vocab_size()
        if self.vocab_size > 65_535 or self._tok.token_to_id(EOS_TEXT) != EOS:
            raise RuntimeError("tokenizer does not fit the uint16 / eos=0 contract")

    def encode(self, text: str) -> np.ndarray:
        """Token ids of ``text`` (no end marker)."""
        return np.asarray(self._tok.encode(text, add_special_tokens=False).ids, dtype=np.uint16)

    def encode_batch(self, texts: Sequence[str]) -> list[np.ndarray]:
        encs = self._tok.encode_batch(list(texts), add_special_tokens=False)
        return [np.asarray(e.ids, dtype=np.uint16) for e in encs]

    def decode(self, ids: Sequence[int] | np.ndarray) -> str:
        ids = [int(i) for i in ids if int(i) != EOS]
        return self._tok.decode(ids, skip_special_tokens=False)

    def token_bytes(self) -> list[bytes]:
        """The raw byte string of every token id (``<|eos|>`` -> b"")."""
        from tokenizers import pre_tokenizers  # noqa: F401  (alphabet mapping below)

        byte_decoder = {c: b for b, c in _bytes_to_unicode().items()}
        out: list[bytes] = []
        for i in range(self.vocab_size):
            piece = self._tok.id_to_token(i)
            if i == EOS or piece is None:
                out.append(b"")
            else:
                out.append(bytes(byte_decoder[ch] for ch in piece))
        return out


def _bytes_to_unicode() -> dict[int, str]:
    """GPT-2's reversible byte -> printable-character map used by ByteLevel."""
    bs = list(range(ord("!"), ord("~") + 1)) + list(range(ord("¡"), ord("¬") + 1)) \
        + list(range(ord("®"), ord("ÿ") + 1))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return dict(zip(bs, (chr(c) for c in cs)))
