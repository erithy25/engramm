"""Local learning (U4) end to end in the app in a real browser: a taught word shows up in the memory dialog under
"Learned on this computer", "forget that" takes it back, a style wish is learned, and the reset button clears the
learning state (also on disk). Skipped when Node or Playwright is missing."""

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
  const say = async (msg, expect) => {
    const before = await page.locator('.msg.assistant').count();
    await page.fill('#input', msg);
    await page.press('#input', 'Enter');
    await page.waitForFunction(n => {
      const all = document.querySelectorAll('.msg.assistant');
      return all.length > n && all[all.length - 1].querySelector('.text[data-done]');
    }, before, { timeout: 30000 });
    const text = await page.locator('.msg.assistant').last().innerText();
    out.push({ msg, ok: expect.every(e => text.includes(e)), text });
  };
  const learned = async () => {
    await page.click('#openMemory');
    await page.waitForSelector('#learningBox');
    await page.waitForTimeout(300);
    const t = await page.locator('#learningBox').last().innerText();
    return t;
  };
  const close = async () => { await page.keyboard.press('Escape'); await page.waitForTimeout(200); };
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#status').classList.contains('ready'), null, { timeout: 30000 });
  await say('a zorbel is a kind of bird', ['now I know', 'zorbel']);
  let t = await learned();
  out.push({ msg: 'dialog shows the taught word', ok: t.includes('zorbel'), text: t });
  await close();
  await say('forget that', ['forgotten']);
  await page.click('#openMemory');
  const gone = await page.waitForFunction(() => {
    const boxes = document.querySelectorAll('#learningBox');
    const t = boxes.length ? boxes[boxes.length - 1].innerText : '';
    return !t.includes('zorbel') && t.includes('Nothing learned yet');
  }, null, { timeout: 10000 }).then(() => true, () => false);
  out.push({ msg: 'forget that removes it', ok: gone, text: '' });
  await close();
  await say('shorter answers please', ['shorter']);
  t = await learned();
  out.push({ msg: 'style wish is learned', ok: !t.includes('Nothing learned yet'), text: t });
  await page.locator('#learningBox button.forget').last().click();
  await page.waitForFunction(() => { const b = document.querySelectorAll('#learningBox'); return b[b.length - 1].innerText.includes('Nothing learned yet'); },
                             null, { timeout: 10000 });
  out.push({ msg: 'reset button clears it', ok: true, text: '' });
  await close();
  out.push({ msg: 'no page errors', ok: errors.length === 0, text: errors.join(' | ') });
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_learning_in_the_app(tmp_path, corpus):  # noqa: F811
    node, env = _node_playwright()
    env = {**env, "TMPDIR": os.environ.get("TMPDIR", str(tmp_path))}
    svc = ChatService(tmp_path / "unused")
    svc.bot = _bot(corpus)
    svc.assistant = Assistant(svc.bot, clock=lambda: dt.datetime(2026, 10, 5, 10, 0))
    svc.assistant.learner = Learner(tmp_path / "learn.json")
    svc.mode = "full"
    server = serve(svc, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    script = tmp_path / "learn.js"
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
    state = json.loads((tmp_path / "learn.json").read_text()) if (tmp_path / "learn.json").exists() else {}
    assert not state.get("ops"), state                    # the reset reached the file on disk
