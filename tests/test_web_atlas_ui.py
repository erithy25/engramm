"""Internet access in the app, in a real browser: the sidebar says "off", the network dialog
switches the shelf and the feeds on, a question the local reading cannot answer is answered from
the (local) shelf with its source, date and channel chip, news come from the feed index, and the
network log lists bucket fetches — never the question. Skipped without Node + Playwright."""

from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import threading
import time

import pytest

from engramm.app.server import ChatService, serve
from engramm.chat.dialog import Assistant
from engramm.web.atlas import Atlas
from engramm.web.egress import Egress, NetworkLog, PythonBackend
from engramm.web.feeds import FeedRefresher, Item
from tests.test_chat_flows import _bot, corpus  # noqa: F401  (fixture)
from tests.test_chat_ui import _node_playwright
from tests.test_web_atlas import shelf_pack  # noqa: F401  (fixture)

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
  await page.waitForSelector('#netLabel');
  check('sidebar says off', (await page.locator('#netLabel').innerText()) === 'off');
  let text = await say('When was the Zorblax Bridge opened?');
  check('offline: no answer from the internet', !text.includes('1931'), text);
  await page.click('#openNetwork');
  await page.waitForSelector('#netShelf');
  check('all switches off', !(await page.isChecked('#netShelf')) && !(await page.isChecked('#netFeeds'))
        && !(await page.isChecked('#netMessenger')));
  check('shelf info', (await page.locator('[data-channel=shelf] .channel-info').innerText()).includes('as of 2026-09-27'));
  check('empty log', await page.isVisible('#netLogEmpty'));
  await page.click('#netShelf');
  await page.waitForFunction(() => document.querySelector('#netShelf').checked);
  await page.click('#netFeeds');
  await page.waitForSelector('#feedList');
  check('feeds: default selection', (await page.locator('#feedList input:checked').count()) === 3);
  await page.keyboard.press('Escape');
  check('sidebar says on', (await page.locator('#netLabel').innerText()) === 'on');
  text = await say('When was the Zorblax Bridge opened?');
  check('shelf answer', text.includes('1931') && text.includes('Wikipedia · Zorblax Bridge · as of 2026-09-20')
        && text.includes('via shelf'), text);
  text = await say("what's the latest news?");
  check('news', text.includes('Quorvia opens new rail line') && text.includes('via news feed'), text);
  await page.click('#openNetwork');
  await page.waitForSelector('#netLog');
  const log = await page.locator('#netLog').innerText();
  check('log lists buckets, never the question', log.includes('bucket') && !log.includes('Zorblax')
        && !log.includes('opened'), log);
  await page.screenshot({ path: shot, fullPage: true });
  await page.click('#netShelf');
  await page.waitForFunction(() => !document.querySelector('#netShelf').checked);
  await page.click('#netFeeds');
  await page.waitForFunction(() => !document.querySelector('#netFeeds').checked);
  await page.keyboard.press('Escape');
  check('sidebar says off again', (await page.locator('#netLabel').innerText()) === 'off');
  check('no page errors', errors.length === 0, errors.join(' | '));
  await browser.close();
  console.log(JSON.stringify(out));
})().catch(e => { console.error(e); process.exit(1); });
"""


@pytest.mark.skipif(_node_playwright() is None, reason="Node.js with Playwright not installed")
def test_internet_access_in_the_browser(tmp_path, corpus, shelf_pack, monkeypatch):  # noqa: F811
    node, env = _node_playwright()
    env = {**env, "TMPDIR": os.environ.get("TMPDIR", str(tmp_path))}
    monkeypatch.setattr(FeedRefresher, "start", lambda self: None)
    monkeypatch.setattr(FeedRefresher, "stop", lambda self: None)
    monkeypatch.setattr(FeedRefresher, "refresh_now", lambda self: {})
    svc = ChatService(tmp_path / "unused")
    svc.bot = _bot(corpus)
    svc.assistant = Assistant(svc.bot, clock=lambda: dt.datetime(2026, 10, 1, 14, 5))
    svc.mode = "full"
    svc.egress = Egress(settings_path=tmp_path / "network.json", log=NetworkLog(tmp_path / "network.log"),
                        backend=PythonBackend())
    svc.atlas = Atlas(svc.egress, shelf_pack, tmp_path / "state")
    svc.assistant.atlas = svc.atlas
    now = int(time.time())
    svc.atlas.feeds.add([Item("bbc-world", "g1", "Quorvia opens new rail line", "The line links two cities.",
                              "https://www.bbc.co.uk/news/1", now - 3600)])
    server = serve(svc, port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    script = tmp_path / "net.js"
    script.write_text(SCRIPT)
    shot = tmp_path / "network.png"
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
    if os.environ.get("ENGRAMM_NET_SHOT"):
        import shutil
        shutil.copy(shot, os.environ["ENGRAMM_NET_SHOT"])
