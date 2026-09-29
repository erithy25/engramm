// Highlight the download for the visitor's system. No cookies, no tracking.
"use strict";
(() => {
  const ua = navigator.userAgent.toLowerCase();
  const os = ua.includes("windows") ? "windows" : ua.includes("mac") ? "mac" : ua.includes("linux") ? "linux" : null;
  if (!os) return;
  const el = document.querySelector(`.platform[data-os="${os}"]`);
  if (el) {
    el.classList.add("mine");
    el.parentElement.prepend(el);
  }
})();
