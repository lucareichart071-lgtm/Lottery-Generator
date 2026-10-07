const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("./logik.js");

function seeded(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32);
}

test("zufallstipp ist gültig", () => {
  const rand = seeded(1);
  for (let i = 0; i < 500; i++) {
    const t = L.zufallstipp(rand);
    assert.equal(new Set(t).size, 6);
    assert.deepEqual(t, [...t].sort((a, b) => a - b));
    assert.ok(t.every((z) => z >= 1 && z <= 49));
  }
});

test("Filterregeln wie in Python", () => {
  const f = (t, l = null) => L.istBeliebtesMuster(t, l);
  assert.deepEqual(f([3, 14, 25, 36, 40, 47]), []);
  assert.deepEqual(f([1, 5, 12, 19, 25, 31]), [L.GRUENDE.geburtstage]);
  assert.deepEqual(f([10, 11, 12, 13, 30, 45]), [L.GRUENDE.folge]);
  assert.deepEqual(f([4, 13, 22, 31, 40, 49]), [L.GRUENDE.abstaende]);
  assert.deepEqual(f([36, 37, 38, 40, 41, 42]), [L.GRUENDE.zeile_spalte]);
  assert.deepEqual(f([2, 9, 16, 23, 30, 44]), [L.GRUENDE.zeile_spalte]);
  assert.deepEqual(f([1, 9, 17, 25, 33, 49]), [L.GRUENDE.diagonale]);
  assert.deepEqual(f([3, 14, 25, 36, 40, 47], [3, 14, 25, 1, 2, 4]), [L.GRUENDE.letzte]);
});

test("smarterTipp verletzt keine Regel", () => {
  const rand = seeded(2);
  const letzte = [5, 7, 19, 24, 33, 46];
  for (let i = 0; i < 1000; i++) {
    assert.deepEqual(L.istBeliebtesMuster(L.smarterTipp(letzte, rand), letzte), []);
  }
});

test("Gewinnklassen", () => {
  const z = { zahlen: [1, 2, 3, 4, 5, 6], superzahl: 7 };
  const k = (tipp, sz) => L.auswertung(tipp, sz, z).klasse;
  assert.equal(k([1, 2, 3, 4, 5, 6], 7), 1);
  assert.equal(k([1, 2, 3, 4, 5, 6], 0), 2);
  assert.equal(k([1, 2, 3, 4, 5, 40], 7), 3);
  assert.equal(k([1, 2, 3, 4, 5, 40], 0), 4);
  assert.equal(k([1, 2, 3, 4, 40, 41], 7), 5);
  assert.equal(k([1, 2, 3, 4, 40, 41], 0), 6);
  assert.equal(k([1, 2, 3, 40, 41, 42], 7), 7);
  assert.equal(k([1, 2, 3, 40, 41, 42], 0), 8);
  assert.equal(k([1, 2, 40, 41, 42, 43], 7), 9);
  assert.equal(k([1, 2, 40, 41, 42, 43], 0), null);
  assert.equal(k([1, 2, 3, 4, 5, 6], null), 2);
  const a = L.auswertung([1, 2, 3, 40, 41, 42], 7, z);
  assert.equal(a.richtige, 3);
  assert.equal(a.szTreffer, true);
});

test("Wahrscheinlichkeiten", () => {
  const p = L.erwarteteVerteilung();
  assert.ok(Math.abs(p.reduce((a, b) => a + b, 0) - 1) < 1e-12);
  assert.ok(Math.abs(p[6] - 1 / 13983816) < 1e-15);
  assert.ok(Math.abs(1 / L.gewinnWahrscheinlichkeit() - 31.4) < 0.5);
});

test("Häufigkeiten und Ziehungstage", () => {
  const h = L.haeufigkeiten([{ zahlen: [1, 2, 3, 4, 5, 6] }, { zahlen: [1, 7, 8, 9, 10, 11] }]);
  assert.equal(h.length, 49);
  assert.equal(h[0], 2);
  assert.equal(h[48], 0);
  // Dienstag, 6.10.2026 -> Mi 7.10., Sa 10.10., Mi 14.10.
  assert.deepEqual(L.naechsteZiehungstage(new Date(2026, 9, 6, 21, 0), 3),
    ["2026-10-07", "2026-10-10", "2026-10-14"]);
  // Samstag zählt mit
  assert.deepEqual(L.naechsteZiehungstage(new Date(2026, 9, 10, 9, 0), 1), ["2026-10-10"]);
});
