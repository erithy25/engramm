"""The chat app (engramm/app) end to end in a real browser on a small corpus: greeting and the
name question, the name flow from the bug report, a fact question with its source chip and
whole-sentence answer, a pronoun follow-up, small talk, a calculation, the memory dialog with
exact forgetting, the language switch and a reload that keeps the conversation. Skipped when Node
or Playwright is missing."""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import threading

import pytest

from engramm.app.server import ChatService, serve
from engramm.chat.dialog import Assistant
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)
from tests.test_chat_ui import _node_playwright

SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], shot = process.argv[3];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
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
    const ok = expect.every(e => text.includes(e)) && (!avoid || avoid.every(e => !text.includes(e)));
    out.push({ msg, ok, text });
  };
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#status').classList.contains('ready'), null, { timeout: 30000 });
  out.push({ msg: 'english ui', ok: (await page.locator('h1').innerText()) === 'How can I help?', text: '' });
  await say('hi', ["your name"]);
  await say('Erik', ['Erik', 'remembered']);
  await say("What's my name?", ['Your name is Erik.', 'you told me']);
  await say('Who invented the telephone?', ['Alexander Graham Bell invented the telephone.', 'Wikipedia · Telephone']);
  await say('Where was he born?', ['Alexander Graham Bell was born in Edinburgh.', 'understood as: Where was Alexander Graham Bell born?']);
  await say('lol', [], ['remembered', 'remember that']);   // a short reaction, nothing stored
  await say('What is 12 times 7?', ['84', 'calculated']);
  await page.click('#openMemory');
  await page.waitForSelector('#memoryList li button.forget');
  const items = await page.locator('#memoryList li').allInnerTexts();
  out.push({ msg: 'memory list', ok: items.length === 1 && items[0].includes('Erik'), text: items.join(' | ') });
  await page.click('#memoryList li button.forget');
  await page.waitForFunction(() => document.querySelectorAll('#memoryList li button.forget').length === 0);
  await page.keyboard.press('Escape');
  await say("What's my name?", ["haven't told me your name"], ['Erik.']);
  await page.click('#toggleLang');
  out.push({ msg: 'german ui', ok: (await page.locator('#newChat').innerText()).includes('Neuer Chat'), text: '' });
  await page.reload();
  await page.waitForFunction(() => document.querySelectorAll('.msg.assistant').length >= 8);
  out.push({ msg: 'reload keeps chat, language', ok: (await page.locator('#newChat').innerText()).includes('Neuer Chat'), text: '' });
  await page.screenshot({ path: shot, fullPage: true });
  out.push({ msg: 'no page errors', ok: errors.length === 0, text: errors.join(' | ') });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_app_in_the_browser(tmp_path, corpus):  # noqa: F811
    node, env = _node_playwright()
    env = {**env, "TMPDIR": os.environ.get("TMPDIR", str(tmp_path))}
    svc = ChatService(tmp_path / "unused")
    svc.bot = _bot(corpus)
    svc.assistant = Assistant(svc.bot, clock=lambda: dt.datetime(2026, 9, 29, 14, 5))
    svc.mode = "full"
    server = serve(svc, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    script = tmp_path / "ui.js"
    script.write_text(SCRIPT)
    shot = tmp_path / "app.png"
    try:
        res = subprocess.run([node, str(script), f"http://127.0.0.1:{server.server_address[1]}/", str(shot)],
                             env=env, capture_output=True, text=True, timeout=240)
    finally:
        server.shutdown()
        server.server_close()
    assert res.returncode == 0, res.stderr[-3000:]
    steps = json.loads(res.stdout.strip().splitlines()[-1])
    bad = [s for s in steps if not s["ok"]]
    assert not bad, bad
    if os.environ.get("ENGRAMM_UI_SHOT"):
        shutil.copy(shot, os.environ["ENGRAMM_UI_SHOT"])
