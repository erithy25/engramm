"use strict";

(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const easeInOut = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
  const easeOut = (t) => 1 - Math.pow(1 - t, 3);

  /* Writes a style only when the value actually changes, so idle frames cost nothing. */
  const setStyle = (el, prop, value) => {
    if (!el) return;
    const cache = el.__styleCache || (el.__styleCache = {});
    if (cache[prop] === value) return;
    cache[prop] = value;
    if (prop.charCodeAt(0) === 45) el.style.setProperty(prop, value);
    else el.style[prop] = value;
  };
  const setClass = (el, name, on) => {
    if (el && el.classList.contains(name) !== on) el.classList.toggle(name, on);
  };

  /* ---------------- Smooth scrolling ---------------- */
  let lenis = null;
  if (!reduceMotion && typeof window.Lenis === "function") {
    try {
      lenis = new window.Lenis({ lerp: 0.14, smoothWheel: true, wheelMultiplier: 1 });
    } catch (err) {
      lenis = null;
    }
  }
  const scrollToY = (y) => {
    if (lenis) lenis.scrollTo(y, { duration: 1.2 });
    else window.scrollTo({ top: y, behavior: reduceMotion ? "auto" : "smooth" });
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (!a) return;
    const id = a.getAttribute("href");
    if (!id || id.length < 2) return;
    const target = document.querySelector(id);
    if (!target) return;
    e.preventDefault();
    if (target.hidden) target.hidden = false;
    const y = id === "#top" || id === "#story" ? 0 : target.getBoundingClientRect().top + window.scrollY - (id === "#platforms" ? 120 : 0);
    scrollToY(y);
  });

  /* ---------------- Letter splitting ---------------- */
  const splitLetters = (el) => {
    const lines = el.innerHTML.split(/<br\s*\/?>/i).map((html) => {
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      return tmp.textContent.trim();
    });
    el.setAttribute("aria-label", lines.join(" "));
    el.replaceChildren();
    let i = 0;
    lines.forEach((line, li) => {
      const lineSpan = document.createElement("span");
      lineSpan.className = `line line${li + 1}`;
      lineSpan.setAttribute("aria-hidden", "true");
      line.split(" ").forEach((word, wi, words) => {
        const w = document.createElement("span");
        w.className = "word";
        for (const ch of word) {
          const l = document.createElement("span");
          l.className = "ltr";
          l.textContent = ch;
          l.style.setProperty("--i", String(i));
          i += 1;
          w.appendChild(l);
        }
        lineSpan.appendChild(w);
        if (wi < words.length - 1) lineSpan.appendChild(document.createTextNode(" "));
      });
      el.appendChild(lineSpan);
      if (li < lines.length - 1) el.appendChild(document.createElement("br"));
    });
  };
  $$("[data-letters], [data-letters-view]").forEach(splitLetters);

  /* ---------------- Pointer ---------------- */
  const pointer = { x: 0, y: 0, sx: 0, sy: 0 };
  window.addEventListener("pointermove", (e) => {
    pointer.x = (e.clientX / window.innerWidth) * 2 - 1;
    pointer.y = (e.clientY / window.innerHeight) * 2 - 1;
  }, { passive: true });

  /* ---------------- Hero intro ---------------- */
  const hero = $("[data-hero]");
  const startHero = () => hero && hero.classList.add("is-in");
  if (document.fonts && document.fonts.ready) {
    Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 900))]).then(() => requestAnimationFrame(startHero));
  } else {
    startHero();
  }
  if (hero) $(".hero__title", hero).style.setProperty("--base", "150ms");

  /* ---------------- Elements ---------------- */
  const nav = $("[data-nav]");
  const themed = $$("[data-nav-theme]");
  const stage = $("[data-stage]");
  const sticky = $("[data-sticky]");
  const stack = $("[data-stack]");
  const stackWrap = $(".stack-wrap");
  const photo = $("[data-pane-photo]");
  const photoImg = $("[data-pane-img]");
  const scenes = $$("[data-pane-scene]");
  const photoClip = $("[data-pane-clip]");
  const skyBox = $("[data-sky]");
  const shade = $(".pane__shade");
  const layers = $$(".pane:not(.pane--photo)").map((el) => ({ el, i: parseFloat(el.style.getPropertyValue("--i")) || 0 }));
  const photoDim = $("[data-pane-dim]");
  const stackHit = $("[data-stack-hit]");
  const stackHint = $("[data-stack-hint]");
  const chaptersBox = $("[data-chapters]");
  const chapters = $$("[data-chapter]");
  const rail = $("[data-rail]");
  const railButtons = $$("[data-goto]");
  const wires = $$(".wire");
  const uiViews = $$(".ui__view");
  const statement = $(".statement");
  const statementGlow = $(".statement__glow");
  const wordsHost = $("[data-words]");
  const floatSection = $("[data-float]");
  const media = $("[data-demo-media]");
  const tiltEl = $("[data-tilt]");
  const glare = $(".demo__glare");
  const demoBg = $(".demo__bg");

  /* ---------------- Cached layout: measured on resize, never per frame ---------------- */
  const skyVars = { top: 0.1, h: 0.58, right: 0.13 };
  const box = { vw: 0, vh: 0, winH: 0, stageTop: 0, stageH: 0, wordsTop: 0, wordsH: 0, floatTop: 0, floatH: 0, rows: [], themed: [] };
  const docTop = (el) => el.getBoundingClientRect().top + window.scrollY;

  /* ---------------- Skywriting: a prop plane writes the E in smoke ---------------- */
  const sky = (() => {
    const root = $("[data-sky]");
    if (!root) return null;
    const trail = $("[data-sky-trail]", root);
    const aged = $("[data-sky-aged]", root);
    const live = $("[data-sky-live]", root);
    const pathE = $("[data-sky-e]", root);
    const pathIn = $("[data-sky-in]", root);
    const pathOut = $("[data-sky-out]", root);
    if (!trail || !aged || !live || !pathE || !pathIn || !pathOut || typeof window.Path2D !== "function") return null;
    const tctx = trail.getContext("2d");
    const actx = aged.getContext("2d");
    const lctx = live.getContext("2d");
    if (!tctx || !actx || !lctx) return null;

    const VB = { x: 300, y: 220, w: 900, h: 620 };
    const STEP = 2;
    const SPEED = 0.5;
    const EMIT_LAG = 34;
    const TEX_COUNT = 6;

    const rng = (seed) => {
      let s = seed | 0;
      return () => {
        s = (s + 0x6d2b79f5) | 0;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
      };
    };

    const sample = (path) => {
      const len = path.getTotalLength();
      const n = Math.max(2, Math.ceil(len / STEP) + 1);
      const xs = new Float32Array(n);
      const ys = new Float32Array(n);
      for (let i = 0; i < n; i += 1) {
        const pt = path.getPointAtLength(Math.min(len, i * STEP));
        xs[i] = pt.x;
        ys[i] = pt.y;
      }
      return { len, n, xs, ys };
    };
    const at = (S, s) => {
      const f = clamp(s, 0, S.len) / STEP;
      const i = Math.min(S.n - 2, Math.floor(f));
      const u = Math.min(1, f - i);
      return { x: S.xs[i] + (S.xs[i + 1] - S.xs[i]) * u, y: S.ys[i] + (S.ys[i + 1] - S.ys[i]) * u };
    };
    const heading = (S, s) => {
      const a = at(S, s - 5);
      const b = at(S, s + 5);
      return Math.atan2(b.y - a.y, b.x - a.x);
    };

    const E = sample(pathE);
    const IN = sample(pathIn);
    const OUT = sample(pathOut);

    /* soft, irregular smoke puffs, generated once */
    const textures = [];
    for (let v = 0; v < TEX_COUNT; v += 1) {
      const c = document.createElement("canvas");
      c.width = 128;
      c.height = 128;
      const g = c.getContext("2d");
      const r = rng(101 + v * 17);
      for (let k = 0; k < 7; k += 1) {
        const cx = 64 + (r() - 0.5) * 40;
        const cy = 64 + (r() - 0.5) * 40;
        const rad = 20 + r() * 22;
        const grd = g.createRadialGradient(cx, cy, 0, cx, cy, rad);
        grd.addColorStop(0, "rgba(255,255,255,0.5)");
        grd.addColorStop(0.45, "rgba(255,255,255,0.26)");
        grd.addColorStop(1, "rgba(255,255,255,0)");
        g.fillStyle = grd;
        g.fillRect(0, 0, 128, 128);
      }
      textures.push(c);
    }

    /* every puff along the E, deterministic so redraws match exactly */
    const puffs = [];
    const r = rng(7);
    const normalAt = (s) => {
      const a = heading(E, s);
      return { nx: -Math.sin(a), ny: Math.cos(a) };
    };
    for (let s = 0; s <= E.len; s += 2.6) {
      const p = at(E, s);
      const n = normalAt(s);
      const j = Math.sin(s * 0.045 + 1.3) * 2.6 + Math.sin(s * 0.13) * 1.2 + (r() - 0.5) * 2.4;
      const big = r() > 0.9 ? 12 * r() : 0;
      puffs.push({ s, x: p.x + n.nx * j, y: p.y + n.ny * j, d: 20 + r() * 10 + big, a: 0.2 + r() * 0.16, v: (r() * TEX_COUNT) | 0, rot: r() * Math.PI * 2, haze: false });
    }
    for (let s = 0; s <= E.len; s += 8) {
      const p = at(E, s);
      const n = normalAt(s);
      const j = (r() - 0.5) * 12;
      puffs.push({ s: s + 0.1, x: p.x + n.nx * j, y: p.y + n.ny * j, d: 54 + r() * 30, a: 0.05 + r() * 0.05, v: (r() * TEX_COUNT) | 0, rot: r() * Math.PI * 2, haze: true });
    }
    puffs.sort((a, b) => a.s - b.s);

    const plane = {
      body: new Path2D("M 18 0 C 16 -2.6 8 -3.4 0 -3.2 L -14 -1.6 L -18.5 -1.1 L -18.5 1.1 L -14 1.6 L 0 3.2 C 8 3.4 16 2.6 18 0 Z"),
      wings: new Path2D("M 6.5 -3 L 4.2 -24 C 2 -25.4 -1.6 -25.4 -3.4 -24 L -4.2 -3 Z M 6.5 3 L 4.2 24 C 2 25.4 -1.6 25.4 -3.4 24 L -4.2 3 Z"),
      tail: new Path2D("M -12.5 -1.4 L -14.6 -9 C -15.8 -9.8 -17.4 -9.8 -18.2 -9 L -17.8 -1.2 Z M -12.5 1.4 L -14.6 9 C -15.8 9.8 -17.4 9.8 -18.2 9 L -17.8 1.2 Z"),
    };

    let scale = 1;
    let drawn = 0;
    let frontier = 0;
    let agedDone = false;
    let state = reduceMotion ? "done" : "wait";
    let delay = 900;
    let t = 0;
    let ang = null;
    let bank = 0;

    const base = (ctx) => ctx.setTransform(scale, 0, 0, scale, -VB.x * scale, -VB.y * scale);
    const drawPuff = (ctx, p, k, alphaK, dx, dy) => {
      const d = p.d * k;
      const c = Math.cos(p.rot) * scale;
      const s = Math.sin(p.rot) * scale;
      ctx.globalAlpha = p.a * alphaK;
      ctx.globalCompositeOperation = p.haze ? "destination-over" : "source-over";
      ctx.setTransform(c, s, -s, c, (p.x + dx - VB.x) * scale, (p.y + dy - VB.y) * scale);
      ctx.drawImage(textures[p.v], -d / 2, -d / 2, d, d);
    };
    const drawTrailTo = (f) => {
      while (drawn < puffs.length && puffs[drawn].s <= f) {
        drawPuff(tctx, puffs[drawn], 1, 1, 0, 0);
        drawn += 1;
      }
      tctx.globalAlpha = 1;
      tctx.globalCompositeOperation = "source-over";
    };
    const renderAged = () => {
      actx.setTransform(1, 0, 0, 1, 0, 0);
      actx.clearRect(0, 0, aged.width, aged.height);
      for (const p of puffs) drawPuff(actx, p, 1.45, 0.6, -3 - Math.sin(p.rot * 3) * 2, -1.5 + Math.cos(p.rot * 2));
      actx.globalAlpha = 1;
      actx.globalCompositeOperation = "source-over";
    };
    const clearLive = () => {
      lctx.setTransform(1, 0, 0, 1, 0, 0);
      lctx.clearRect(0, 0, live.width, live.height);
    };

    /* the canvases are sized for the full-bleed hero, so they stay sharp when the card shrinks */
    const resize = () => {
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const frac = parseFloat(getComputedStyle(root).getPropertyValue("--sky-h")) || 0.58;
      const heroH = (sticky ? sticky.clientHeight : window.innerHeight) || window.innerHeight;
      const hPx = Math.max(64, Math.round(Math.min(2200, heroH * frac * dpr)));
      const wPx = Math.round((hPx * VB.w) / VB.h);
      if (trail.width === wPx && trail.height === hPx) return;
      for (const c of state === "done" ? [trail, aged] : [trail, aged, live]) {
        c.width = wPx;
        c.height = hPx;
      }
      scale = hPx / VB.h;
      drawn = 0;
      tctx.setTransform(1, 0, 0, 1, 0, 0);
      tctx.clearRect(0, 0, wPx, hPx);
      drawTrailTo(frontier);
      if (agedDone) renderAged();
    };
    resize();

    if (reduceMotion) {
      frontier = E.len;
      drawTrailTo(frontier);
      renderAged();
      agedDone = true;
      root.classList.add("is-aged");
    }

    const drawLive = (pose, freshFrom, freshTo) => {
      clearLive();
      if (freshTo - freshFrom > 1) {
        base(lctx);
        lctx.globalAlpha = 1;
        lctx.beginPath();
        const a = at(E, freshFrom);
        lctx.moveTo(a.x, a.y);
        for (let s = freshFrom + 3; s < freshTo; s += 3) {
          const p = at(E, s);
          lctx.lineTo(p.x, p.y);
        }
        const b = at(E, freshTo);
        lctx.lineTo(b.x, b.y);
        const grd = lctx.createLinearGradient(a.x, a.y, b.x, b.y);
        grd.addColorStop(0, "rgba(255,255,255,0)");
        grd.addColorStop(1, "rgba(255,255,255,0.9)");
        lctx.lineCap = "round";
        lctx.lineJoin = "round";
        lctx.strokeStyle = grd;
        lctx.lineWidth = 4.5;
        lctx.stroke();
      }
      if (pose) {
        base(lctx);
        lctx.translate(pose.x, pose.y);
        lctx.rotate(ang);
        lctx.scale(0.86, 0.86 * (1 - bank));
        lctx.globalAlpha = 1;
        lctx.fillStyle = "rgba(8,10,16,0.94)";
        lctx.fill(plane.body);
        lctx.fill(plane.wings);
        lctx.fill(plane.tail);
        lctx.globalAlpha = 0.25 + Math.random() * 0.4;
        lctx.fillRect(18.4, -7.5, 1.3, 15);
        lctx.globalAlpha = 1;
      }
    };

    const update = (dt) => {
      if (state === "done") return;
      if (state === "wait") {
        if (!hero || !hero.classList.contains("is-in")) return;
        delay -= dt;
        if (delay > 0) return;
        state = "fly";
      }
      t += dt;
      const d = t * SPEED;
      let pose = null;
      let target = ang;
      let v = -1;
      if (d < IN.len) {
        pose = at(IN, d);
        target = heading(IN, d);
      } else if (d < IN.len + E.len) {
        v = d - IN.len;
        pose = at(E, v);
        target = heading(E, v);
      } else if (d < IN.len + E.len + OUT.len) {
        v = d - IN.len;
        const o = d - IN.len - E.len;
        pose = at(OUT, o);
        target = heading(OUT, o);
      } else {
        v = Infinity;
      }

      if (pose) {
        if (ang === null) ang = target;
        let diff = target - ang;
        while (diff > Math.PI) diff -= Math.PI * 2;
        while (diff < -Math.PI) diff += Math.PI * 2;
        ang += diff * (1 - Math.exp(-dt / 60));
        const turn = dt > 0 ? Math.abs(diff) / dt : 0;
        bank += (Math.min(0.34, turn * 9) - bank) * (1 - Math.exp(-dt / 140));
      }

      if (v > 0) {
        const f = clamp(v - EMIT_LAG, 0, E.len);
        if (f > frontier) {
          frontier = f;
          drawTrailTo(frontier);
        }
      }
      const freshTo = v > 0 ? Math.min(v, E.len) : 0;
      const freshFrom = Math.max(0, frontier - 6);
      drawLive(pose, freshFrom, freshTo);

      if (!agedDone && frontier >= E.len) {
        agedDone = true;
        renderAged();
        root.classList.add("is-aged");
      }
      if (!pose && agedDone) {
        clearLive();
        live.width = 0;
        live.height = 0;
        state = "done";
      }
    };
    return { update, resize };
  })();

  /* ---------------- Stage: the photo shrinks into the layered stack ---------------- */
  let activeChapter = -2;
  let activeView = -1;
  let stageTheme = "clear";
  const SHRINK = 0.12;
  const CH = [0.17, 0.38, 0.59, 0.8];
  const rot = { x: 0, y: 0 };
  const chapterTilt = [
    { x: 0, y: 0 },
    { x: 0, y: 0 },
    { x: 3, y: 8 },
    { x: -3, y: -8 },
    { x: 4, y: 14 },
  ];

  /* Grab the stack and turn it: the pointer drives the angle directly, release hands the
     momentum to a soft spring that brings the cards back to their resting pose. */
  const grab = { down: false, id: null, x: 0, y: 0, rawX: 0, rawY: 0, tX: 0, tY: 0, offX: 0, offY: 0, velX: 0, velY: 0, lift: 0, used: false, samples: [] };
  const LIM_X = 38;
  const LIM_Y = 78;
  const softLimit = (v, l) => l * Math.tanh(v / l);
  const unsoft = (v, l) => {
    const q = clamp(v / l, -0.995, 0.995);
    return l * 0.5 * Math.log((1 + q) / (1 - q));
  };
  const endGrab = () => {
    if (!grab.down) return;
    grab.down = false;
    document.documentElement.classList.remove("is-grabbing");
    const now = performance.now();
    const recent = grab.samples.filter((smp) => now - smp.t <= 90);
    if (recent.length > 1) {
      const a = recent[0];
      const b = recent[recent.length - 1];
      const span = Math.max(16, b.t - a.t);
      grab.velX = clamp(((b.x - a.x) / span) * 1000, -220, 220);
      grab.velY = clamp(((b.y - a.y) / span) * 1000, -320, 320);
    } else {
      grab.velX = 0;
      grab.velY = 0;
    }
    grab.samples = [];
  };
  if (stackHit) {
    stackHit.addEventListener("pointerdown", (e) => {
      if (e.pointerType === "mouse" && e.button !== 0) return;
      grab.down = true;
      grab.id = e.pointerId;
      grab.x = e.clientX;
      grab.y = e.clientY;
      grab.tX = grab.offX;
      grab.tY = grab.offY;
      grab.rawX = unsoft(grab.offX, LIM_X);
      grab.rawY = unsoft(grab.offY, LIM_Y);
      grab.velX = 0;
      grab.velY = 0;
      grab.used = true;
      grab.samples = [{ t: performance.now(), x: grab.tX, y: grab.tY }];
      try { stackHit.setPointerCapture(e.pointerId); } catch (err) { /* capture is optional */ }
      document.documentElement.classList.add("is-grabbing");
      if (e.pointerType === "mouse") e.preventDefault();
    });
    stackHit.addEventListener("pointermove", (e) => {
      if (!grab.down || e.pointerId !== grab.id) return;
      const dx = e.clientX - grab.x;
      const dy = e.clientY - grab.y;
      grab.x = e.clientX;
      grab.y = e.clientY;
      const touch = e.pointerType !== "mouse";
      grab.rawY += dx * (touch ? 0.42 : 0.34);
      grab.rawX -= dy * (touch ? 0.14 : 0.24);
      grab.tX = softLimit(grab.rawX, LIM_X);
      grab.tY = softLimit(grab.rawY, LIM_Y);
      const now = performance.now();
      grab.samples.push({ t: now, x: grab.tX, y: grab.tY });
      while (grab.samples.length > 2 && now - grab.samples[0].t > 120) grab.samples.shift();
    });
    for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
      stackHit.addEventListener(type, (e) => { if (e.pointerId === grab.id) endGrab(); });
    }
    window.addEventListener("blur", endGrab);
  }
  const updateGrab = (dt) => {
    if (grab.down) {
      const k = 1 - Math.exp(-dt / 26);
      grab.offX += (grab.tX - grab.offX) * k;
      grab.offY += (grab.tY - grab.offY) * k;
    } else if (grab.offX !== 0 || grab.offY !== 0 || grab.velX !== 0 || grab.velY !== 0) {
      const K = 30;
      const C = 2 * Math.sqrt(K) * 0.8;
      const sec = dt / 1000;
      const steps = Math.max(1, Math.ceil(sec / 0.008));
      const h = sec / steps;
      for (let i = 0; i < steps; i += 1) {
        grab.velX += (-K * grab.offX - C * grab.velX) * h;
        grab.velY += (-K * grab.offY - C * grab.velY) * h;
        grab.offX += grab.velX * h;
        grab.offY += grab.velY * h;
      }
      grab.offX = clamp(grab.offX, -LIM_X * 1.15, LIM_X * 1.15);
      grab.offY = clamp(grab.offY, -LIM_Y * 1.15, LIM_Y * 1.15);
      if (Math.abs(grab.offX) < 0.005 && Math.abs(grab.offY) < 0.005 && Math.abs(grab.velX) < 0.05 && Math.abs(grab.velY) < 0.05) {
        grab.offX = 0;
        grab.offY = 0;
        grab.velX = 0;
        grab.velY = 0;
      }
    }
    grab.lift += ((grab.down ? 1 : 0) - grab.lift) * (1 - Math.exp(-dt / (grab.down ? 140 : 320)));
    if (!grab.down && grab.lift < 0.001) grab.lift = 0;
  };

  const setView = (v) => {
    if (v === activeView) return;
    activeView = v;
    wires.forEach((w) => w.classList.toggle("is-on", Number(w.dataset.view) === v));
    uiViews.forEach((u) => u.classList.toggle("is-on", Number(u.dataset.view) === v));
  };
  const setChapter = (c) => {
    if (c === activeChapter) return;
    activeChapter = c;
    chapters.forEach((el, i) => el.classList.toggle("is-on", i === c));
    railButtons.forEach((b, i) => b.classList.toggle("is-on", i === c));
    if (c >= 0) setView([0, 0, 1, 2][c]);
  };

  railButtons.forEach((b) => {
    b.addEventListener("click", () => {
      const k = Number(b.dataset.goto);
      scrollToY(box.stageTop + (box.stageH - box.vh) * (CH[k] + 0.04));
    });
  });

  const renderStage = (sy) => {
    if (!stage || !stack || !photo) return;
    const vw = box.vw;
    const vh = box.vh;
    const top = box.stageTop - sy;
    if (top + box.stageH < -50 || top > vh) return;
    const p = clamp(-top / Math.max(1, box.stageH - vh));
    const small = vw <= 640;

    let W = Math.min(520, vw * (small ? 0.78 : 0.42));
    W = Math.min(W, vh * 0.6);
    if (!small) W = Math.max(W, Math.min(320, vw - 60));
    const H = W * 0.62;
    const cyFinal = vh * (small ? 0.33 : 0.36);

    /* full-bleed photo shrinks into a card: transforms and a clip while moving, real card size once it rests */
    const t1 = reduceMotion ? (p > 0.01 ? 1 : 0) : easeInOut(clamp(p / SHRINK));
    const cy = lerp(vh / 2, cyFinal, t1);
    const aspect = W / H;
    const wide = vw / vh > aspect;
    const cw = wide ? vh * aspect : vw;
    const ch = wide ? vh : vw / aspect;
    const kEnd = Math.max(cw, ch * 16 / 9) / Math.max(vw, vh * 16 / 9);
    const skyH = skyVars.h * vh;
    const skyTop = skyVars.top * vh;
    const skyLeft = (1 - skyVars.right) * vw - skyH * 0.7419;
    if (t1 >= 0.999) {
      const f = W / cw;
      const mapX = (x) => ((x - vw / 2) * kEnd + vw / 2 - (vw - cw) / 2) * f;
      const mapY = (y) => ((y - vh / 2) * kEnd + vh / 2 - (vh - ch) / 2) * f;
      setStyle(photo, "width", `${W.toFixed(1)}px`);
      setStyle(photo, "height", `${H.toFixed(1)}px`);
      setStyle(photo, "transform", "translate(-50%, -50%)");
      setStyle(photoClip, "width", `${W.toFixed(1)}px`);
      setStyle(photoClip, "height", `${H.toFixed(1)}px`);
      setStyle(photoClip, "left", "0px");
      setStyle(photoClip, "top", "0px");
      setStyle(photoClip, "borderRadius", "10px");
      for (const s of scenes) setStyle(s, "transform", "translate(-50%, -50%)");
      setStyle(shade, "transform", "translate(-50%, -50%)");
      setStyle(skyBox, "left", `${mapX(skyLeft).toFixed(2)}px`);
      setStyle(skyBox, "top", `${mapY(skyTop).toFixed(2)}px`);
      setStyle(skyBox, "height", `${(skyH * kEnd * f).toFixed(2)}px`);
    } else {
      const scale = lerp(1, W / cw, t1);
      const clipW = lerp(vw, cw, t1);
      const clipH = lerp(vh, ch, t1);
      setStyle(photo, "width", `${vw}px`);
      setStyle(photo, "height", `${vh}px`);
      setStyle(photo, "transform", `translate(-50%, -50%) scale(${scale.toFixed(4)})`);
      setStyle(photoClip, "width", `${clipW.toFixed(1)}px`);
      setStyle(photoClip, "height", `${clipH.toFixed(1)}px`);
      setStyle(photoClip, "left", `${((vw - clipW) / 2).toFixed(1)}px`);
      setStyle(photoClip, "top", `${((vh - clipH) / 2).toFixed(1)}px`);
      setStyle(photoClip, "borderRadius", `${((10 * t1) / scale).toFixed(1)}px`);
      const sceneScale = lerp(1, kEnd, t1);
      for (const s of scenes) setStyle(s, "transform", `translate(-50%, -50%) scale(${sceneScale.toFixed(4)})`);
      setStyle(shade, "transform", `translate(-50%, -50%) scale(${(clipW / vw).toFixed(4)}, ${(clipH / vh).toFixed(4)})`);
      setStyle(skyBox, "left", `${skyLeft.toFixed(2)}px`);
      setStyle(skyBox, "top", `${skyTop.toFixed(2)}px`);
      setStyle(skyBox, "height", `${skyH.toFixed(2)}px`);
    }
    setStyle(photoDim, "opacity", (t1 * 0.42).toFixed(3));
    if (photoImg) {
      const k = 1 - t1;
      setStyle(photoImg, "transform", `translate(-50%, -50%) translate3d(${(-pointer.sx * 12 * k).toFixed(1)}px, ${(-pointer.sy * 8 * k).toFixed(1)}px, 0) scale(${lerp(1.06, 1, t1).toFixed(4)})`);
    }

    /* hero copy leaves */
    const out = clamp(p / 0.05);
    if (hero) {
      setStyle(hero, "opacity", (1 - out).toFixed(3));
      setStyle(hero, "transform", `translate3d(0, ${(-clamp(p / 0.08) * 90).toFixed(1)}px, 0)`);
      setStyle(hero, "visibility", out >= 1 ? "hidden" : "visible");
    }
    stageTheme = out < 0.5 ? "clear" : "dark";

    /* the stack fans out behind and in front of the photo */
    const r = reduceMotion ? (p > 0.01 ? 1 : 0) : easeOut(clamp((p - 0.07) / 0.1));
    setStyle(stack, "--pw", `${W.toFixed(1)}px`);
    setStyle(stack, "--ph", `${H.toFixed(1)}px`);
    const gap = (small ? 26 : 60) * r * (1 + grab.lift * 0.45);
    for (const l of layers) {
      setStyle(l.el, "transform", `translate(-50%, -50%) translateZ(${(l.i * gap).toFixed(2)}px)`);
      setStyle(l.el, "opacity", r.toFixed(3));
    }
    setStyle(stack, "--k", (W / 520).toFixed(4));

    let c = -1;
    for (let i = 0; i < CH.length; i += 1) if (p >= CH[i]) c = i;
    setChapter(c);
    if (c < 0 && r > 0.4) setView(0);

    const tilt = chapterTilt[c + 1];
    const follow = 1 - grab.lift;
    const targetX = (11 + tilt.x - pointer.sy * 3 * follow) * r;
    const targetY = (-34 + tilt.y + pointer.sx * 5 * follow) * r;
    const k = reduceMotion ? 1 : 0.075;
    rot.x += (targetX - rot.x) * k;
    rot.y += (targetY - rot.y) * k;
    if (r === 0) { rot.x = 0; rot.y = 0; }
    const turnX = rot.x + grab.offX * r;
    const turnY = rot.y + grab.offY * r;
    setStyle(stack, "transform", `translate3d(0, ${(cy - vh / 2).toFixed(1)}px, ${(grab.lift * 36).toFixed(2)}px) rotateX(${turnX.toFixed(2)}deg) rotateY(${turnY.toFixed(2)}deg)`);
    setStyle(stackWrap, "perspectiveOrigin", `50% ${cy.toFixed(0)}px`);

    setClass(rail, "is-on", r > 0.9 && p < 0.995);

    /* the grab surface sits over the resting cards only */
    const live = !reduceMotion && r > 0.9 && t1 >= 0.999 && p < 0.995;
    if (!live && grab.down) endGrab();
    setClass(stackHit, "is-live", live);
    setStyle(stackHit, "left", `${(vw / 2 - W * 0.85).toFixed(0)}px`);
    setStyle(stackHit, "top", `${(cy - H * 0.95).toFixed(0)}px`);
    setStyle(stackHit, "width", `${(W * 1.7).toFixed(0)}px`);
    setStyle(stackHit, "height", `${(H * 1.75).toFixed(0)}px`);
    setClass(stackHint, "is-on", live && c >= 0 && !grab.used);
    setStyle(stackHint, "--hint-top", `${(cyFinal + H * 0.62 + (small ? 14 : 22)).toFixed(0)}px`);
    setStyle(chaptersBox, "--chapters-top", `${(cyFinal + H * 0.62 + (small ? 40 : 56)).toFixed(0)}px`);
  };

  /* ---------------- Statement ---------------- */
  let words = [];
  if (wordsHost) {
    const text = wordsHost.textContent.trim();
    wordsHost.setAttribute("aria-label", text);
    wordsHost.replaceChildren();
    text.split(/\s+/).forEach((word, i, arr) => {
      const span = document.createElement("span");
      span.className = "w";
      if (/^(account\.|ask\.)$/.test(word)) span.classList.add("is-key");
      span.setAttribute("aria-hidden", "true");
      span.textContent = word;
      wordsHost.appendChild(span);
      if (i < arr.length - 1) wordsHost.appendChild(document.createTextNode(" "));
    });
    words = $$(".w", wordsHost);
  }
  let litCount = -1;
  const renderStatement = (sy) => {
    if (!statement || !words.length) return;
    const top = box.wordsTop - sy;
    const vh = box.winH;
    if (top + box.wordsH < -vh * 0.5 || top > vh) return;
    const prog = reduceMotion ? 1 : clamp((vh * 0.85 - top) / (box.wordsH + vh * 0.25));
    const lit = Math.round(prog * words.length * 1.05);
    if (lit !== litCount) {
      litCount = lit;
      words.forEach((w, i) => setClass(w, "is-on", i < lit));
    }
    setStyle(statementGlow, "opacity", prog.toFixed(2));
  };

  /* ---------------- Marquee ---------------- */
  const rows = $$("[data-marquee]").map((row) => {
    const track = $(".marquee__track", row);
    const original = Array.from(track.children);
    for (let n = 0; n < 3; n += 1) original.forEach((c) => track.appendChild(c.cloneNode(true)));
    return { row, track, dir: Number(row.dataset.marquee) || 1, offset: 0, unit: 0, top: 0, h: 0 };
  });
  let prevScroll = window.scrollY;
  let velocity = 0;
  const renderMarquee = (sy, dt) => {
    velocity = lerp(velocity, Math.abs(sy - prevScroll) / Math.max(dt, 1), 0.12);
    prevScroll = sy;
    if (reduceMotion) return;
    for (const m of rows) {
      const top = m.top - sy;
      if (top + m.h < 0 || top > box.winH || !m.unit) continue;
      m.offset = (m.offset + (0.045 + velocity * 0.9) * dt) % m.unit;
      const x = m.dir > 0 ? -m.offset : m.offset - m.unit;
      m.track.style.transform = `translate3d(${x.toFixed(1)}px, 0, 0)`;
    }
  };

  /* ---------------- Floating tiles ---------------- */
  const tiles = $$(".tile").map((el) => {
    const z = parseFloat(el.style.getPropertyValue("--z")) || 0.5;
    return { el, z, s: (0.62 + z * 0.45).toFixed(3) };
  });
  const floatTitle = $("[data-letters-view]");
  if (floatTitle && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) if (e.isIntersecting) { floatTitle.classList.add("is-in"); io.disconnect(); }
    }, { threshold: 0.5 });
    io.observe(floatTitle);
  } else if (floatTitle) {
    floatTitle.classList.add("is-in");
  }
  const renderTiles = (sy) => {
    if (!floatSection || reduceMotion) return;
    const top = box.floatTop - sy;
    const vh = box.winH;
    if (top + box.floatH < 0 || top > vh) return;
    const prog = clamp((vh - top) / (vh + box.floatH));
    for (const t of tiles) {
      const ty = (prog - 0.5) * -320 * t.z + pointer.sy * 26 * t.z;
      const tx = pointer.sx * 44 * t.z;
      setStyle(t.el, "transform", `translate3d(calc(-50% + ${tx.toFixed(1)}px), calc(-50% + ${ty.toFixed(1)}px), 0) scale(${t.s})`);
    }
  };

  /* ---------------- Demo tilt ---------------- */
  const tilt = { tx: 0, ty: 0, x: 0, y: 0, gx: 0.5, gy: 0, sgx: 0.5, sgy: 0, w: 1000, h: 560 };
  let tiltVisible = false;
  if (media && tiltEl && !reduceMotion) {
    media.addEventListener("pointermove", (e) => {
      const rect = media.getBoundingClientRect();
      tilt.tx = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      tilt.ty = ((e.clientY - rect.top) / rect.height) * 2 - 1;
      const wr = tiltEl.getBoundingClientRect();
      tilt.gx = (e.clientX - wr.left) / wr.width;
      tilt.gy = (e.clientY - wr.top) / wr.height;
      tilt.w = wr.width;
      tilt.h = wr.height;
    }, { passive: true });
    media.addEventListener("pointerleave", () => { tilt.tx = 0; tilt.ty = 0; });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver((entries) => { for (const e of entries) tiltVisible = e.isIntersecting; }).observe(media);
    } else {
      tiltVisible = true;
    }
  }
  const renderTilt = () => {
    if (!tiltVisible || !tiltEl || reduceMotion) return;
    tilt.x = lerp(tilt.x, tilt.tx, 0.08);
    tilt.y = lerp(tilt.y, tilt.ty, 0.08);
    tilt.sgx = lerp(tilt.sgx, tilt.gx, 0.12);
    tilt.sgy = lerp(tilt.sgy, tilt.gy, 0.12);
    setStyle(tiltEl, "transform", `rotateX(${(-tilt.y * 2.6).toFixed(2)}deg) rotateY(${(tilt.x * 3.6).toFixed(2)}deg)`);
    setStyle(glare, "transform", `translate3d(${(tilt.sgx * tilt.w).toFixed(0)}px, ${(tilt.sgy * tilt.h).toFixed(0)}px, 0)`);
    setStyle(demoBg, "transform", `translate3d(${(-tilt.x * 14).toFixed(1)}px, ${(-tilt.y * 10).toFixed(1)}px, 0) scale(1.04)`);
  };

  /* ---------------- Navigation ---------------- */
  let lastY = window.scrollY;
  const updateNav = (sy) => {
    if (!nav) return;
    if (sy > lastY + 3 && sy > 200) setClass(nav, "is-hidden", true);
    else if (sy < lastY - 3 || sy < 200) setClass(nav, "is-hidden", false);
    lastY = sy;
    const probe = sy + 40;
    let theme = null;
    for (const s of box.themed) {
      if (s.top <= probe && s.bottom > probe) { theme = s.theme; break; }
    }
    theme = theme || stageTheme;
    if (nav.dataset.theme !== theme) nav.dataset.theme = theme;
  };

  /* ---------------- Footer light ---------------- */
  const footerWord = $(".footer__word");
  if (footerWord) {
    footerWord.parentElement.addEventListener("pointermove", (e) => {
      const rect = footerWord.getBoundingClientRect();
      footerWord.style.setProperty("--fx", `${(((e.clientX - rect.left) / rect.width) * 100).toFixed(1)}%`);
    }, { passive: true });
  }

  /* ---------------- Demo ---------------- */
  const demo = (() => {
    const root = $("[data-demo]");
    if (!root) return null;
    const log = $("[data-log]", root);
    const typed = $("[data-typed]", root);
    const sourceBox = $("[data-source]", root);
    const memoryList = $("[data-memory]", root);
    const memCount = $("[data-mem-count]", root);
    const tabs = $$("[data-tab]", root);
    const demoMedia = $(".demo__media", root);

    const BASE = ["You like to be called Alex", "You're vegetarian"];
    const LENA = "Your sister is called Lena";
    const bell = { doc: "Alexander Graham Bell", ref: "Wikipedia, lead section" };
    const S = {
      ask: {
        memory: BASE,
        context: [],
        turns: [
          {
            you: "Who invented the telephone?",
            bot: { answer: "Alexander Graham Bell", quote: "“…is credited with patenting the first practical telephone.”", chips: [{ t: "Wikipedia: Alexander Graham Bell" }, { t: "Sure", k: "sure" }] },
            source: { ...bell, quote: "“Alexander Graham Bell … is credited with patenting the first practical telephone.”" },
          },
          {
            you: "When was he born?",
            bot: { answer: "3 March 1847", quote: "“Alexander Graham Bell (March 3, 1847 – August 2, 1922) was a Scottish-born…”", chips: [{ t: "Wikipedia: Alexander Graham Bell" }, { t: "Sure", k: "sure" }] },
            source: { ...bell, quote: "“Alexander Graham Bell (March 3, 1847 – August 2, 1922)…”" },
          },
        ],
      },
      remember: {
        memory: BASE,
        context: [],
        turns: [
          {
            you: "My sister is called Lena.",
            bot: { answer: "Noted. I'll remember that your sister is called Lena.", chips: [{ t: "Saved to memory", k: "memory" }] },
            source: { none: "Nothing to look up. You told me this." },
            add: LENA,
          },
        ],
      },
      forget: {
        memory: [...BASE, LENA],
        context: [{ you: "My sister is called Lena.", bot: { answer: "Noted. I'll remember that your sister is called Lena.", chips: [{ t: "Saved to memory", k: "memory" }] } }],
        turns: [
          {
            you: "Forget my sister's name.",
            bot: { answer: "Done. The entry is deleted, not hidden.", chips: [{ t: "Removed from memory", k: "memory" }] },
            source: { none: "Deleted from memory and recorded in the log." },
            remove: LENA,
          },
        ],
      },
      admit: {
        memory: BASE,
        context: [],
        turns: [
          {
            you: "How many people live in Atlantis?",
            bot: { answer: "I don't know. I found no source that answers this.", unknown: true },
            source: { none: "No source found, so no answer was given." },
          },
        ],
      },
    };
    const ORDER = ["ask", "remember", "forget", "admit"];
    const TYPE_MS = 42;
    const estimate = (sc) => sc.turns.reduce((sum, t) => sum + t.you.length * TYPE_MS + 300 + 350 + 700 + 2300 + (t.remove ? 1300 : 0), 0) + 1400;

    const el = (tag, cls, text) => {
      const n = document.createElement(tag);
      if (cls) n.className = cls;
      if (text !== undefined) n.textContent = text;
      return n;
    };
    const renderBot = (bot) => {
      const li = el("li", "msg msg--bot");
      li.appendChild(el("p", bot.unknown ? "msg__answer is-unknown" : "msg__answer", bot.answer));
      if (bot.quote) li.appendChild(el("blockquote", "quote", bot.quote));
      if (bot.chips && bot.chips.length) {
        const meta = el("div", "msg__meta");
        for (const c of bot.chips) meta.appendChild(el("span", c.k ? `chip chip--${c.k}` : "chip", c.t));
        li.appendChild(meta);
      }
      return li;
    };
    const renderSource = (src) => {
      if (!src) { sourceBox.replaceChildren(el("p", "inspect__empty", "Nothing looked up yet.")); return; }
      if (src.none) { sourceBox.replaceChildren(el("p", "inspect__empty", src.none)); return; }
      sourceBox.replaceChildren(el("p", "inspect__doc", src.doc), el("blockquote", "quote", src.quote), el("p", "inspect__ref", src.ref));
    };
    const memItem = (text) => {
      const li = el("li");
      li.dataset.text = text;
      const span = el("span");
      span.appendChild(document.createTextNode(text));
      li.appendChild(span);
      return li;
    };
    const setMemory = (items) => {
      memoryList.replaceChildren(...items.map(memItem));
      memCount.textContent = String(items.length);
    };
    const trim = () => { while (log.children.length > 8) log.removeChild(log.firstChild); };

    let clock = 0;
    let waits = [];
    let run = 0;
    let current = null;
    let startAt = 0;
    let total = 1;
    let inView = false;
    const wait = (ms) => new Promise((resolve) => waits.push({ t: clock + ms, resolve }));
    const active = () => inView && !document.hidden;

    const setTab = (name) => {
      tabs.forEach((t) => {
        const on = t.dataset.tab === name;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        const bar = $(".demo__bar i", t);
        if (bar) bar.style.transform = "scaleX(0)";
      });
    };

    const play = async (name) => {
      run += 1;
      const my = run;
      waits = [];
      current = name;
      const sc = S[name];
      setTab(name);
      log.replaceChildren();
      typed.textContent = "";
      setMemory(sc.memory);
      renderSource(null);
      for (const c of sc.context) {
        log.appendChild(el("li", "msg msg--you", c.you));
        log.appendChild(renderBot(c.bot));
      }
      startAt = clock;
      total = estimate(sc);

      if (reduceMotion) {
        for (const t of sc.turns) {
          log.appendChild(el("li", "msg msg--you", t.you));
          log.appendChild(renderBot(t.bot));
          renderSource(t.source);
          if (t.add) setMemory([...sc.memory, t.add]);
          if (t.remove) setMemory(sc.memory.filter((m) => m !== t.remove));
        }
        trim();
        return;
      }

      await wait(500);
      if (my !== run) return;
      for (const t of sc.turns) {
        for (const ch of t.you) {
          typed.textContent += ch;
          await wait(TYPE_MS);
          if (my !== run) return;
        }
        await wait(300);
        if (my !== run) return;
        typed.textContent = "";
        log.appendChild(el("li", "msg msg--you", t.you));
        trim();
        await wait(350);
        if (my !== run) return;
        const thinking = el("li", "msg msg--bot");
        const dots = el("span", "thinking");
        dots.append(el("i"), el("i"), el("i"));
        thinking.appendChild(dots);
        log.appendChild(thinking);
        trim();
        await wait(700);
        if (my !== run) return;
        thinking.replaceWith(renderBot(t.bot));
        renderSource(t.source);
        if (t.add) {
          const li = memItem(t.add);
          li.classList.add("is-new");
          li.firstChild.appendChild(el("em", "", "New"));
          memoryList.appendChild(li);
          memCount.textContent = String(memoryList.children.length);
        }
        if (t.remove) {
          const li = $$("li", memoryList).find((n) => n.dataset.text === t.remove);
          if (li) {
            await wait(400);
            if (my !== run) return;
            li.classList.add("is-striking");
            await wait(900);
            if (my !== run) return;
            li.classList.add("is-gone");
            memCount.textContent = String(memoryList.children.length - 1);
          }
        }
        await wait(2300);
        if (my !== run) return;
      }
      await wait(900);
      if (my !== run) return;
      play(ORDER[(ORDER.indexOf(name) + 1) % ORDER.length]);
    };

    tabs.forEach((t, i) => {
      t.addEventListener("click", () => play(t.dataset.tab));
      t.addEventListener("keydown", (e) => {
        if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
        const n = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
        n.focus();
        play(n.dataset.tab);
      });
    });

    if ("IntersectionObserver" in window && demoMedia) {
      new IntersectionObserver((entries) => {
        for (const e of entries) inView = e.isIntersecting;
      }, { threshold: 0.35 }).observe(demoMedia);
    } else {
      inView = true;
    }

    const tick = (dt) => {
      if (!active()) return;
      clock += dt;
      if (waits.length) {
        const due = waits.filter((w) => w.t <= clock);
        if (due.length) {
          waits = waits.filter((w) => w.t > clock);
          due.forEach((w) => w.resolve());
        }
      }
      if (current && !reduceMotion) {
        const tab = tabs.find((t) => t.dataset.tab === current);
        const bar = tab && $(".demo__bar i", tab);
        if (bar) setStyle(bar, "transform", `scaleX(${clamp((clock - startAt) / total).toFixed(3)})`);
      }
    };

    play("ask");
    return { play, tick };
  })();

  $$("[data-demo-link]").forEach((a) => a.addEventListener("click", () => demo && demo.play(a.dataset.demoLink)));

  /* ---------------- Early access ---------------- */
  const detectOs = () => {
    const uaData = navigator.userAgentData;
    const platform = ((uaData && uaData.platform) || navigator.platform || "").toLowerCase();
    const ua = navigator.userAgent.toLowerCase();
    if (/iphone|ipad|android/.test(ua)) return null;
    if (platform.includes("mac") || ua.includes("mac os")) return "mac-arm";
    if (platform.includes("win") || ua.includes("windows")) return "windows";
    if (/fedora|suse|rhel|centos/.test(ua)) return "linux-rpm";
    if (platform.includes("linux") || ua.includes("linux")) return "linux";
    return null;
  };
  const names = { "mac-arm": "macOS", windows: "Windows", linux: "Linux", "linux-rpm": "Linux" };
  const platformsBox = $("[data-platforms]");
  const toggle = $("[data-platforms-toggle]");
  const primary = $("[data-primary-download]");
  if (toggle && platformsBox) {
    toggle.addEventListener("click", () => {
      const open = platformsBox.hidden;
      platformsBox.hidden = !open;
      toggle.setAttribute("aria-expanded", String(open));
    });
  }
  const os = detectOs();
  if (os && primary) {
    const link = $(`[data-os="${os}"]`);
    if (link) {
      link.classList.add("is-yours");
      primary.href = link.href;
      primary.textContent = `Download for ${names[os]}`;
      primary.addEventListener("click", () => {
        if (platformsBox) platformsBox.hidden = false;
        if (toggle) toggle.setAttribute("aria-expanded", "true");
      });
    }
  }

  /* ---------------- Measuring ---------------- */
  const measure = () => {
    box.vw = sticky ? sticky.clientWidth : document.documentElement.clientWidth;
    box.vh = sticky ? sticky.clientHeight : window.innerHeight;
    box.winH = window.innerHeight;
    if (skyBox) {
      const cs = getComputedStyle(skyBox);
      skyVars.top = parseFloat(cs.getPropertyValue("--sky-top")) || 0.1;
      skyVars.h = parseFloat(cs.getPropertyValue("--sky-h")) || 0.58;
      skyVars.right = parseFloat(cs.getPropertyValue("--sky-right")) || 0.13;
    }
    if (stage) { box.stageTop = docTop(stage); box.stageH = stage.offsetHeight; }
    if (wordsHost) { box.wordsTop = docTop(wordsHost); box.wordsH = wordsHost.offsetHeight; }
    if (floatSection) { box.floatTop = docTop(floatSection); box.floatH = floatSection.offsetHeight; }
    for (const m of rows) {
      m.top = docTop(m.row);
      m.h = m.row.offsetHeight;
      m.unit = m.track.scrollWidth / 4;
    }
    box.themed = themed.map((s) => {
      const t = docTop(s);
      return { top: t, bottom: t + s.offsetHeight, theme: s.dataset.navTheme };
    });
  };
  let measureQueued = false;
  const queueMeasure = () => {
    if (measureQueued) return;
    measureQueued = true;
    requestAnimationFrame(() => {
      measureQueued = false;
      measure();
      if (sky) sky.resize();
    });
  };
  measure();
  window.addEventListener("resize", queueMeasure);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(queueMeasure);
  if ("ResizeObserver" in window) new ResizeObserver(queueMeasure).observe(document.body);
  window.addEventListener("load", queueMeasure);

  /* ---------------- Main loop ---------------- */
  let prev = performance.now();
  const loop = (now) => {
    const dt = Math.min(100, now - prev);
    prev = now;
    if (lenis) lenis.raf(now);
    const sy = window.scrollY;
    pointer.sx = lerp(pointer.sx, reduceMotion ? 0 : pointer.x, 0.06);
    pointer.sy = lerp(pointer.sy, reduceMotion ? 0 : pointer.y, 0.06);
    if (sky) sky.update(dt);
    updateGrab(dt);
    renderStage(sy);
    renderStatement(sy);
    renderMarquee(sy, dt);
    renderTiles(sy);
    renderTilt();
    updateNav(sy);
    if (demo) demo.tick(dt);
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
})();
