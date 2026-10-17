"""Chat format of Sela-2 (ChatML), shared by the training data (experiments/sela2_data.py) and the desktop app.

A conversation is rendered as token ids, never as text with special markers inside (literal "<|im_start|>" in a
user's message stays ordinary text):

    <|eos|><|im_start|>system\\n…<|im_end|>\\n<|im_start|>sources\\n…<|im_end|>\\n
    <|im_start|>user\\n…<|im_end|>\\n<|im_start|>assistant\\n…<|im_end|>\\n …

<|eos|> opens the context (as every document in training). The loss mask marks the tokens the model learns to
produce in fine-tuning: an assistant turn's text and the <|im_end|> that closes it. Generation stops at <|im_end|>.
Grounded turns put the sources first: ``[1] Title: text`` lines in a ``sources`` message; the assistant cites them
as [1], [2] and answers ``NO_ANSWER`` when they do not contain the answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

EOS, IM_START, IM_END = 0, 1, 2
SPECIAL_TOKENS = ["<|eos|>", "<|im_start|>", "<|im_end|>"] + [f"<|reserved_{i}|>" for i in range(3, 16)]
ROLES = ("system", "sources", "user", "assistant")

SYSTEM = {
    "en": "You are Sela, a small language model trained from scratch in the ENGRAMM project. You run offline on the "
          "user's computer. Answer helpfully, clearly and briefly.",
    "de": "Du bist Sela, ein kleines Sprachmodell, das im ENGRAMM-Projekt von Grund auf trainiert wurde. Du läufst "
          "offline auf dem Computer der Nutzerin oder des Nutzers. Antworte hilfreich, klar und kurz.",
}
SYSTEM_BRIEF = {
    "en": "You are Sela, a small offline assistant. Answer in one to three short sentences.",
    "de": "Du bist Sela, ein kleiner Offline-Assistent. Antworte in ein bis drei kurzen Sätzen.",
}
SYSTEM_GROUNDED = {
    "en": "You are Sela. Answer only from the sources and cite them like [1]. If the sources do not contain the "
          "answer, say: \"My sources don't say.\"",
    "de": "Du bist Sela. Antworte nur aus den Quellen und zitiere sie wie [1]. Wenn die Quellen die Antwort nicht "
          "enthalten, sage: „Meine Quellen sagen dazu nichts.“",
}
NO_ANSWER = {"en": "My sources don't say.", "de": "Meine Quellen sagen dazu nichts."}

# assistant turns that claim another model's identity are not trained on (identity comes from our own data)
FOREIGN_IDENTITY = re.compile(
    r"\b(ChatGPT|GPT-[345]|OpenAI|Claude|Anthropic|Llama|LLaMA|Meta AI|Qwen|Alibaba Cloud|Tongyi|Gemini|Bard|"
    r"Google DeepMind|DeepSeek|Mistral AI|SmolLM|Hugging ?Face|HuggingFace|Microsoft Copilot|Phi-[234])\b")


@dataclass
class Message:
    role: str
    text: str


def sources_block(sources: list[tuple[str, str]]) -> str:
    """``[(title, text), …]`` → numbered lines ``[1] title: text``."""
    return "\n".join(f"[{i}] {t}: {x}".strip() if t else f"[{i}] {x}".strip() for i, (t, x) in enumerate(sources, 1))


def render(tok, messages: list[Message] | list[dict], add_generation_prompt: bool = False,
           max_tokens: int | None = None) -> tuple[list[int], list[int]]:
    """(ids, mask) of a conversation. ``tok`` encodes plain text (engramm.lm.tokenizer.LMTokenizer with the Sela-2
    vocabulary). ``add_generation_prompt``: end with an open assistant turn (for the app). Raises ValueError for an
    unknown role. ``max_tokens``: None or the limit; longer conversations raise ValueError (training drops them)."""
    ids, mask = [EOS], [0]
    nl = [int(t) for t in tok.encode("\n")]
    for m in messages:
        role, text = (m.role, m.text) if isinstance(m, Message) else (m["role"], m["text"])
        if role not in ROLES:
            raise ValueError(f"unknown chat role {role!r}")
        head = [IM_START] + [int(t) for t in tok.encode(role + "\n")]
        body = [int(t) for t in tok.encode(text)]
        ids += head
        mask += [0] * len(head)
        learn = 1 if role == "assistant" else 0
        ids += body + [IM_END]
        mask += [learn] * (len(body) + 1)
        ids += nl
        mask += [0] * len(nl)
    if add_generation_prompt:
        head = [IM_START] + [int(t) for t in tok.encode("assistant\n")]
        ids += head
        mask += [0] * len(head)
    if max_tokens is not None and len(ids) > max_tokens:
        raise ValueError(f"conversation of {len(ids)} tokens exceeds {max_tokens}")
    return ids, mask


def clean_reply(text: str) -> str:
    """The assistant text as shown: stray role headers or special-token text removed, whitespace trimmed."""
    text = re.sub(r"<\|(im_start|im_end|eos|reserved_\d+)\|>", "", text)
    return text.strip()


CITE = re.compile(r"\[(\d{1,2})\]")


def citations(text: str) -> list[int]:
    return [int(n) for n in CITE.findall(text)]
