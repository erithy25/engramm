"""A failed load is shown on the page, not only in a tooltip: the panel names the error (with the file and line
where it happened), "Try again" asks the server to load again, and the text can be copied. Skipped when Node or
Playwright is missing."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading

import pytest

from engramm.app.server import ChatService, serve
from tests.test_chat_ui import _node_playwright

SCRIPT = r"""
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2], shot = process.argv[3];
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1100, height: 760 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  const out = [];
  await page.goto(url);
  await page.waitForSelector('#loadError', { timeout: 20000 });
  const text = await page.textContent('#loadErrorText');
  out.push({ msg: 'error text on the page', ok: text.includes('No knowledge pack') && text.includes('app/server.py:'), text });
  out.push({ msg: 'status pill says it', ok: (await page.textContent('#statusText')).includes('error while loading') });
  out.push({ msg: 'send is off', ok: await page.isDisabled('#send') });
  await page.click('#retryLoad');
  await page.waitForFunction(() => document.querySelector('#retryLoad') && !document.querySelector('#retryLoad').disabled);
  await page.waitForSelector('#loadError', { timeout: 20000 });
  const reloads = await (await fetch(url + 'api/health')).json();
  out.push({ msg: 'still an error after trying again (no pack)', ok: !!reloads.error, text: reloads.error });
  await page.screenshot({ path: shot });
  await page.setViewportSize({ width: 390, height: 760 });
  const box = await page.locator('#loadError').boundingBox();
  out.push({ msg: 'fits a phone width', ok: box !== null && box.width <= 390, text: JSON.stringify(box) });
  out.push({ msg: 'no page errors', ok: errors.length === 0, text: errors.join(' | ') });
  console.log(JSON.stringify(out));
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
"""


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_load_error_panel(tmp_path):
    node, env = _node_playwright()
    env = {**env, "TMPDIR": os.environ.get("TMPDIR", str(tmp_path))}
    svc = ChatService(tmp_path / "unused", pack=tmp_path / "nopack", memory_path=tmp_path / "chat_memory.log")
    loads = []
    real_load = svc.load
    svc.load = lambda: (loads.append(1), real_load())
    server = serve(svc, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    svc.start_loading()
    script = tmp_path / "ui.js"
    script.write_text(SCRIPT, encoding="utf-8")
    shot = tmp_path / "load_error.png"
    try:
        res = subprocess.run([node, str(script), f"http://127.0.0.1:{server.server_address[1]}/", str(shot)],
                             env=env, capture_output=True, text=True, timeout=240)
    finally:
        server.shutdown()
        server.server_close()
    assert res.returncode == 0, res.stderr[-3000:]
    steps = json.loads(res.stdout.strip().splitlines()[-1])
    assert not [s for s in steps if not s["ok"]], steps
    assert len(loads) == 2                    # the start and "Try again"
    if os.environ.get("ENGRAMM_UI_SHOT"):
        shutil.copy(shot, os.environ["ENGRAMM_UI_SHOT"])
