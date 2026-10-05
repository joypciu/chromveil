// ChromVeil context init — reduce automation signals (Patchright/Playwright persistent context).
(() => {
  const patch = () => {
    try {
      if (navigator.webdriver !== undefined) {
        Object.defineProperty(navigator, "webdriver", {
          get: () => undefined,
          configurable: true,
        });
      }
    } catch (e) {}
    try {
      const el = document.documentElement;
      if (el && el.getAttribute("webdriver")) el.removeAttribute("webdriver");
    } catch (e) {}
    try {
      if (!window.chrome) {
        window.chrome = { runtime: {} };
      } else if (!window.chrome.runtime) {
        window.chrome.runtime = {};
      }
    } catch (e) {}
    try {
      const iw = window.innerWidth;
      const ih = window.innerHeight;
      if (iw && ih) {
        const ow = Math.max(iw, iw + 12);
        const oh = Math.max(ih, ih + 88);
        Object.defineProperty(window, "outerWidth", { get: () => ow, configurable: true });
        Object.defineProperty(window, "outerHeight", { get: () => oh, configurable: true });
      }
    } catch (e) {}
  };
  patch();
  document.addEventListener("DOMContentLoaded", patch, { once: true });
})();
