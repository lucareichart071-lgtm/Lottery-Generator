(function (root) {
  "use strict";
  const MAX_VERSUCHE = 10000;
  const GRUENDE = {
    geburtstage: "nur Zahlen bis 31 (Geburtstage)",
    folge: "4 oder mehr aufeinanderfolgende Zahlen",
    abstaende: "gleichmäßige Abstände",
    zeile_spalte: "alle in einer Zeile oder Spalte des Tippscheins",
    diagonale: "alle auf einer Diagonale des Tippscheins",
    letzte: "3 oder mehr Zahlen aus der letzten Ziehung",
  };
  const KLASSEN = [[6, true, 1], [6, false, 2], [5, true, 3], [5, false, 4],
    [4, true, 5], [4, false, 6], [3, true, 7], [3, false, 8], [2, true, 9]];

  function zufallstipp(rand = Math.random) {
    const pool = Array.from({ length: 49 }, (_, i) => i + 1);
    for (let i = 0; i < 6; i++) {
      const j = i + Math.floor(rand() * (49 - i));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    return pool.slice(0, 6).sort((a, b) => a - b);
  }

  const zeile = (z) => Math.floor((z - 1) / 7);
  const spalte = (z) => (z - 1) % 7;
  const einheitlich = (t, f) => new Set(t.map(f)).size === 1;

  function istBeliebtesMuster(tipp, letzte) {
    const t = [...tipp].sort((a, b) => a - b);
    const g = [];
    if (t[5] <= 31) g.push(GRUENDE.geburtstage);
    let lauf = 1, laengster = 1;
    for (let i = 1; i < 6; i++) {
      lauf = t[i] === t[i - 1] + 1 ? lauf + 1 : 1;
      laengster = Math.max(laengster, lauf);
    }
    if (laengster >= 4) g.push(GRUENDE.folge);
    if (new Set(t.slice(1).map((z, i) => z - t[i])).size === 1) g.push(GRUENDE.abstaende);
    if (einheitlich(t, zeile) || einheitlich(t, spalte)) g.push(GRUENDE.zeile_spalte);
    if (einheitlich(t, (z) => zeile(z) - spalte(z)) || einheitlich(t, (z) => zeile(z) + spalte(z))) {
      g.push(GRUENDE.diagonale);
    }
    if (letzte && t.filter((z) => letzte.includes(z)).length >= 3) g.push(GRUENDE.letzte);
    return g;
  }

  function smarterTipp(letzte, rand = Math.random) {
    for (let i = 0; i < MAX_VERSUCHE; i++) {
      const t = zufallstipp(rand);
      if (istBeliebtesMuster(t, letzte).length === 0) return t;
    }
    throw new Error("Kein gültiger Tipp nach " + MAX_VERSUCHE + " Versuchen");
  }

  function auswertung(tipp, superzahl, ziehung) {
    const richtige = tipp.filter((z) => ziehung.zahlen.includes(z)).length;
    const szTreffer = superzahl != null && ziehung.superzahl != null &&
      Number(superzahl) === Number(ziehung.superzahl);
    const k = KLASSEN.find(([r, mitSz]) => r === richtige && (!mitSz || szTreffer));
    return { richtige, szTreffer, klasse: k ? k[2] : null };
  }

  function binom(n, k) {
    let r = 1;
    for (let i = 1; i <= k; i++) r = (r * (n - k + i)) / i;
    return r;
  }

  function erwarteteVerteilung() {
    const gesamt = binom(49, 6);
    return [0, 1, 2, 3, 4, 5, 6].map((k) => (binom(6, k) * binom(43, 6 - k)) / gesamt);
  }

  function gewinnWahrscheinlichkeit() {
    const p = erwarteteVerteilung();
    return p[3] + p[4] + p[5] + p[6] + p[2] * 0.1;
  }

  function haeufigkeiten(ziehungen) {
    const h = new Array(49).fill(0);
    for (const z of ziehungen) for (const n of z.zahlen) h[n - 1]++;
    return h;
  }

  function isoDatum(d) {
    const p = (n) => String(n).padStart(2, "0");
    return d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate());
  }

  function naechsteZiehungstage(heute, n) {
    const tage = [];
    const d = new Date(heute.getFullYear(), heute.getMonth(), heute.getDate());
    while (tage.length < n) {
      if (d.getDay() === 3 || d.getDay() === 6) tage.push(isoDatum(d));
      d.setDate(d.getDate() + 1);
    }
    return tage;
  }

  const api = { GRUENDE, zufallstipp, istBeliebtesMuster, smarterTipp, auswertung,
    erwarteteVerteilung, gewinnWahrscheinlichkeit, haeufigkeiten, naechsteZiehungstage, isoDatum };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lotto = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
