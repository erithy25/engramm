"""U1 (docs/PREREG_CHAT_V2.md): the chat in the dashboard, end to end in a real browser.

Starts the dashboard on a small model and drives Chromium with Playwright (Node):
ask → answer with source; pronoun follow-up; tell a fact; ask it back; forget it;
"I don't know" afterwards and for an unknown entity. Skipped when Node or Playwright
is not installed (``npm i -g playwright``).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading

import numpy as np
import pytest

from engramm.chat import index as v2
from engramm.lm.dashboard import App, load_logged, make_bot, serve
from engramm.lm.model import COMPONENTS, HDCLanguageModel, MixtureSpec
from engramm.lm.stream import build_split
from engramm.lm.tokenizer import LMTokenizer

DOCS = [
    "Paris is the capital of France. The Seine flows through Paris. Paris has 2,100,000 inhabitants.",
    "The telephone was invented by Alexander Graham Bell. He was born in Edinburgh on March 3, 1847.",
    "Mount Everest is the highest mountain on Earth. It lies in the Himalayas.",
    "Tokyo is the capital of Japan. Tokyo is a very large city with many trains.",
]
KEYS = [("wiki", "Paris"), ("wiki", "Telephone"), ("wiki", "Mount Everest"), ("wiki", "Tokyo")]

SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], shot = process.argv[3];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const out = [];
  const say = async (msg, expect, extra) => {
    const before = await page.locator('.bub.bot').count();
    await page.fill('#msg', msg);
    await page.press('#msg', 'Enter');
    await page.waitForFunction(n => document.querySelectorAll('.bub.bot').length > n, before, { timeout: 30000 });
    const last = page.locator('.bub.bot').last();
    const text = await last.innerText();
    const ok = expect.every(e => text.includes(e)) && (!extra || extra.every(e => !text.includes(e)));
    out.push({ msg, ok, text });
  };
  await page.goto(url);
  await page.waitForSelector('#msg');
  await say('Who invented the telephone?', ['Alexander Graham Bell', 'Wikipedia', 'Telephone']);
  await say('Where was he born?', ['Edinburgh', 'verstanden als: Where was Alexander Graham Bell born?']);
  await say('My name is Frotam.', ['Got it']);
  await page.waitForFunction(() => document.querySelector('#learned').innerText.includes('My name is Frotam'));
  await say('What is my name?', ['Frotam', 'Faktengedächtnis', 'Dein Text']);
  await say('Forget my name.', ['forgotten', 'My name is Frotam']);
  await page.waitForFunction(() => !document.querySelector('#learned').innerText.includes('My name is Frotam'));
  await say('What is my name?', ["I don't know"], ['Frotam.']);
  await say('What is the capital of Gunpolris?', ["I don't know"]);
  await page.click('.chip >> nth=0');
  await page.waitForFunction(() => document.querySelectorAll('.bub.bot').length >= 8);
  const chip = await page.locator('.bub.bot').last().innerText();
  out.push({ msg: 'chip', ok: chip.includes('Alexander Graham Bell'), text: chip });
  await page.screenshot({ path: shot, fullPage: true });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


def _node_playwright() -> tuple[str, dict] | None:
    node = shutil.which("node")
    npm = shutil.which("npm")
    if not node or not npm:
        return None
    root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True).stdout.strip()
    env = {**os.environ, "NODE_PATH": root}
    ok = subprocess.run([node, "-e", "require('playwright')"], env=env, capture_output=True).returncode == 0
    return (node, env) if ok else None


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_chat_in_the_browser(tmp_path):
    node, env = _node_playwright()
    tok = LMTokenizer()
    train = build_split(DOCS * 2, KEYS * 2, tok.encode_batch)
    model = HDCLanguageModel.build(train, seed=42, tok=tok,
                                   mixture=MixtureSpec(COMPONENTS, np.full((64, 5), 0.2),
                                                       np.array([2000, 4000, 8000]), 1024.0, 4.0))
    d = tmp_path / "model"
    model.save(d)
    ix, dptr, dpost, sent_doc = v2.build(model.tokens, model.train.doc_starts, tok)
    v2.save(tmp_path / "chat2", ix, dptr, dpost, sent_doc, {"sentences": ix.n})
    lm = load_logged(d)
    app = App(lm, make_bot(lm, tmp_path / "chat2", df_cap=1.0))
    server = serve(app, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    script = tmp_path / "ui.js"
    script.write_text(SCRIPT)
    shot = tmp_path / "chat.png"
    try:
        res = subprocess.run([node, str(script), f"http://127.0.0.1:{server.server_address[1]}/", str(shot)],
                             env=env, capture_output=True, text=True, timeout=180)
    finally:
        server.shutdown()
        lm.log.close()
    assert res.returncode == 0, res.stderr[-2000:]
    steps = json.loads(res.stdout.strip().splitlines()[-1])
    bad = [s for s in steps if not s["ok"]]
    assert not bad, bad
    assert len(steps) == 8 and shot.exists()
    if os.environ.get("ENGRAMM_UI_SHOT"):
        shutil.copy(shot, os.environ["ENGRAMM_UI_SHOT"])
