"""The model choice next to the chat field, end to end in a real browser: ENGRAMM and Sela-1 in one conversation,
the label, hint and reply chip follow the chosen model, the choice survives a reload, and a server without Sela-1
offers it disabled. Skipped when Node or Playwright is missing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading

import pytest

from engramm.app.server import ChatService, serve
from tests.test_chat_app import _Assistant, _Bot, _Sela
from tests.test_chat_ui import _node_playwright

SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], shot = process.argv[3], withSela = process.argv[4] === '1';
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 860 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const out = [];
  const check = (msg, ok, text) => out.push({ msg, ok: Boolean(ok), text: text || '' });
  const say = async (msg) => {
    const before = await page.locator('.msg.assistant').count();
    await page.fill('#input', msg);
    await page.press('#input', 'Enter');
    await page.waitForFunction(n => {
      const all = document.querySelectorAll('.msg.assistant');
      return all.length > n && all[all.length - 1].querySelector('.text[data-done]');
    }, before, { timeout: 30000 });
    return await page.locator('.msg.assistant').last().innerText();
  };
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#status').classList.contains('ready'), null, { timeout: 30000 });
  await page.waitForFunction(() => document.querySelectorAll('#model option').length === 2);
  const selaDisabled = await page.locator('#model option[value="sela-1"]').isDisabled();
  if (!withSela) {
    check('sela offered but disabled', selaDisabled, await page.locator('#model').innerText());
    check('engramm selected', (await page.locator('#model').inputValue()) === 'engramm');
    check('no page errors', errors.length === 0, errors.join(' | '));
    await browser.close();
    console.log(JSON.stringify(out));
    return;
  }
  check('sela enabled', !selaDisabled);
  check('engramm by default', (await page.locator('#model').inputValue()) === 'engramm');
  let text = await say('hello');
  check('engramm answers', text.includes('prev=None'), text);
  await page.selectOption('#model', 'sela-1');
  check('pill shows sela', (await page.locator('#modelPill').innerText()).includes('Sela-1 135M'));
  check('hint warns', (await page.locator('#hint').innerText()).includes('invents facts'));
  text = await say('The town lies on');
  check('sela continues', text.includes('… the river, which runs through the town.') && text.includes('Sela-1 · invented'), text);
  text = await say('What is the capital of France?');
  check('sela question', text.includes('Paris.'), text);
  await page.screenshot({ path: shot, fullPage: false });
  await page.reload();
  await page.waitForFunction(() => document.querySelectorAll('#model option').length === 2);
  await page.waitForFunction(() => document.querySelector('#model').value === 'sela-1', null, { timeout: 10000 });
  check('choice survives reload', (await page.locator('#model').inputValue()) === 'sela-1');
  await page.selectOption('#model', 'engramm');
  text = await say('again');
  check('back to engramm', text.includes('prev=') && !text.includes('Sela-1 · invented'), text);
  await page.click('#toggleLang');
  check('german label', (await page.locator('#model option[value="sela-1"]').innerText()).includes('freier Text'));
  check('no page errors', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


def _run(tmp_path, with_sela: bool):
    node, env = _node_playwright()
    env = {**env, "TMPDIR": os.environ.get("TMPDIR", str(tmp_path))}
    svc = ChatService(tmp_path / "unused")
    svc.bot = _Bot()
    svc.assistant = _Assistant(svc.bot)
    svc.sela_path = (tmp_path / "sela1-135m.npz") if with_sela else None
    svc.sela = _Sela() if with_sela else None
    server = serve(svc, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    script = tmp_path / "sela_ui.js"
    script.write_text(SCRIPT)
    shot = tmp_path / "sela.png"
    try:
        res = subprocess.run([node, str(script), f"http://127.0.0.1:{server.server_address[1]}/", str(shot),
                              "1" if with_sela else "0"], env=env, capture_output=True, text=True, timeout=240)
    finally:
        server.shutdown()
        server.server_close()
    assert res.returncode == 0, res.stderr[-3000:]
    steps = json.loads(res.stdout.strip().splitlines()[-1])
    bad = [s for s in steps if not s["ok"]]
    assert not bad, bad
    return shot


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_model_choice_in_the_browser(tmp_path):
    shot = _run(tmp_path, with_sela=True)
    if os.environ.get("ENGRAMM_UI_SHOT"):
        shutil.copy(shot, os.environ["ENGRAMM_UI_SHOT"])


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_without_sela_the_choice_is_disabled(tmp_path):
    _run(tmp_path, with_sela=False)
