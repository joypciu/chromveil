// Node: chromveil up --port 9222, then:
//   set CHROMVEIL_CDP_URL=http://127.0.0.1:9222
//   node examples/puppeteer_connect.mjs

import puppeteer from "puppeteer-core";

const cdp = process.env.CHROMVEIL_CDP_URL || "http://127.0.0.1:9222";
const browser = await puppeteer.connect({ browserURL: cdp });
const page = await browser.newPage();
await page.goto("https://example.com");
console.log(await page.title());
await browser.disconnect();
