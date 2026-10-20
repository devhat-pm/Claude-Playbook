// Page-side extractor for Claude in Chrome's javascript_tool.
// Paste the whole file as the `text` argument (REPL semantics: the last expression is returned).
// Edit CONFIG first. Returns a JSON string: {url, count, columns, rows}.
// Reads only what is rendered (innerText), skips hidden nodes so display:none text can't ride along.
(() => {
  const CONFIG = {
    table: "table",            // CSS selector for a <table>; picks the largest match
    cards: null,               // OR a selector for repeated cards, e.g. "[data-testid=result-card]"
    cardFields: {              // used only with `cards`: column -> selector inside each card
      name: "h3",
      price: "[data-price]",
      status: ".badge",
    },
    maxRows: 5000,
  };

  const visible = (el) => {
    if (!el) return false;
    const s = window.getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const clean = (t) => (t || "").replace(/\s+/g, " ").trim();

  let columns = [];
  let rows = [];

  if (CONFIG.cards) {
    columns = Object.keys(CONFIG.cardFields);
    rows = Array.from(document.querySelectorAll(CONFIG.cards))
      .filter(visible)
      .slice(0, CONFIG.maxRows)
      .map((card) => columns.map((c) => clean((card.querySelector(CONFIG.cardFields[c]) || {}).innerText)));
  } else {
    const tables = Array.from(document.querySelectorAll(CONFIG.table)).filter(visible);
    if (!tables.length) return JSON.stringify({ error: "no visible table for " + CONFIG.table });
    const t = tables.sort((a, b) => b.rows.length - a.rows.length)[0];
    const head = t.tHead && t.tHead.rows.length ? t.tHead.rows[0] : t.rows[0];
    columns = Array.from(head.cells).map((c, i) => clean(c.innerText) || "col_" + i);
    rows = Array.from(t.tBodies.length ? t.tBodies[0].rows : t.rows)
      .filter((r) => r !== head && visible(r))
      .slice(0, CONFIG.maxRows)
      .map((r) => Array.from(r.cells).map((c) => clean(c.innerText)));
  }

  return JSON.stringify({ url: location.href, count: rows.length, columns, rows });
})();
