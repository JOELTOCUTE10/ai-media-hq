import { JSDOM } from "jsdom";
import { readFileSync } from "fs";

const css = readFileSync("dist/assets/index-iMPNxSat.css", "utf8");
const js = readFileSync("hq_test.js", "utf8");
const dash = readFileSync("/tmp/qa_payloads/dashboard.json", "utf8");
const tasks = JSON.stringify([{ id: 1, title: "QA: verify HQ feed rendering", status: "queued", priority: "medium", created_at: "2026-10-04T21:17:50Z" }]);

const dom = new JSDOM(`<!doctype html><html><head><style>${css}</style></head><body><div id="root"></div></body></html>`, {
  url: "https://hq.local/",
  runScripts: "outside-only",
  pretendToBeVisual: true,
});
const { window } = dom;
const errs = [];
window.addEventListener("error", (e) => errs.push(String(e.error?.stack ?? e.message)));
window.console.error = (...a) => errs.push(a.map(String).join(" "));
window.fetch = (url) => {
  const p = String(url);
  function r(j) { return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(JSON.parse(j)) }); }
  if (p.includes("/api/dashboard")) return r(dash);
  if (p.includes("/api/tasks")) return r(tasks);
  if (p.includes("/api/founder/goals")) return r("[]");
  if (p.includes("/api/health")) return r(JSON.stringify({ status: "ok", ai_provider: "groq" }));
  return r("{}");
};
window.localStorage.setItem("token", "t");
window.sessionStorage.setItem("booted", "1");

window.eval(js); // bundle executes with shims already in place

await new Promise((res) => setTimeout(res, 2500));
const root = window.document.getElementById("root");
const text = root?.textContent ?? "";
console.log("ERRORS:", errs.length ? errs.join(" | ").slice(0, 800) : "none");
console.log("HAS HQ FEED:", text.includes("Live agent activity"));
console.log("HAS EVENT:", text.includes("Org registered"));
console.log("HAS TASKBOARD:", text.includes("Task board"));
console.log("HAS USAGE:", text.includes("Usage & providers"));
console.log("TITLE:", window.document.title);
window.close();
process.exit(0);
