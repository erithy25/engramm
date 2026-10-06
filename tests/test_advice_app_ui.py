"""An unseen problem conversation end to end in the app in a real browser (plan, verification): the situation is
recognised, the reply asks a fitting question, and a request for help gets steps with their source — in English and
German (Wikibooks), health steps with the line to see a doctor or call for help. Skipped when Node or Playwright is
missing."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import threading

import pytest

from engramm.app.server import ChatService, serve
from engramm.chat.dialog import Assistant
from engramm.learn import Learner
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)
from tests.test_chat_ui import _node_playwright

SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  const out = [];
  const say = async (msg, expect, avoid) => {
    const before = await page.locator('.msg.assistant').count();
    await page.fill('#input', msg);
    await page.press('#input', 'Enter');
    await page.waitForFunction(n => {
      const all = document.querySelectorAll('.msg.assistant');
      return all.length > n && all[all.length - 1].querySelector('.text[data-done]');
    }, before, { timeout: 30000 });
    const text = await page.locator('.msg.assistant').last().innerText();
    const ok = expect.every(e => (e instanceof RegExp ? e.test(text) : text.includes(e))) &&
               (!avoid || avoid.every(e => !text.includes(e)));
    out.push({ msg, ok, text });
  };
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#status').classList.contains('ready'), null, { timeout: 30000 });
  await say('my bike has a flat', [/\?/], ["I don't know", 'Tell me more']);
  await say('how do i fix it?', ['•', /tyre|tire/], ['Not really']);
  await page.click('#newChat');
  await page.waitForTimeout(300);
  await say('ich hab mich am herd verbrannt', [/\?|leid|autsch|oh/i], ['Erzähl ruhig mehr']);
  await say('was soll ich tun?', ['Wikibooks', 'Verbrennung', '112']);
  out.push({ msg: 'no page errors', ok: errors.length === 0, text: errors.join(' | ') });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_problem_conversation_in_the_app(tmp_path, corpus):  # noqa: F811
    node, env = _node_playwright()
    env = {**env, "TMPDIR": os.environ.get("TMPDIR", str(tmp_path))}
    svc = ChatService(tmp_path / "unused")
    svc.bot = _bot(corpus)
    svc.assistant = Assistant(svc.bot, clock=lambda: dt.datetime(2026, 10, 6, 10, 0))
    svc.assistant.learner = Learner(tmp_path / "learn.json")
    svc.mode = "full"
    server = serve(svc, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    script = tmp_path / "advice.js"
    script.write_text(SCRIPT)
    try:
        res = subprocess.run([node, str(script), f"http://127.0.0.1:{server.server_address[1]}/"],
                             env=env, capture_output=True, text=True, timeout=240)
    finally:
        server.shutdown()
        server.server_close()
    assert res.returncode == 0, res.stderr[-3000:]
    steps = json.loads(res.stdout.strip().splitlines()[-1])
    bad = [s for s in steps if not s["ok"]]
    assert not bad, bad
