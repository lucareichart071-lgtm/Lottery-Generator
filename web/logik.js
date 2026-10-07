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

  // Berliner Wochentag (0 = So ... 6 = Sa), Stunde, Minute und Datum für einen Zeitpunkt.
  function berlinTeile(jetzt) {
    const teile = {};
    for (const p of new Intl.DateTimeFormat("en-US", { timeZone: "Europe/Berlin", weekday: "short", year: "numeric",
      month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(jetzt)) {
      teile[p.type] = p.value;
    }
    const tage = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
    return { tag: tage[teile.weekday], stunde: Number(teile.hour), minute: Number(teile.minute),
      jahr: Number(teile.year), monat: Number(teile.month), datum: Number(teile.day) };
  }

  // true, wenn die heutige Ziehung (Mi 18:00, Sa 19:00 Berliner Zeit) schon nicht mehr tippbar ist.
  function annahmeschlussVorbei(jetzt) {
    const b = berlinTeile(jetzt);
    const minuten = b.stunde * 60 + b.minute;
    return (b.tag === 3 && minuten >= 18 * 60) || (b.tag === 6 && minuten >= 19 * 60);
  }

  function naechsteZiehungstage(heute, n, heuteGeschlossen) {
    const tage = [];
    const b = berlinTeile(heute);
    const d = new Date(Date.UTC(b.jahr, b.monat - 1, b.datum));
    if (heuteGeschlossen) d.setUTCDate(d.getUTCDate() + 1);
    while (tage.length < n) {
      if (d.getUTCDay() === 3 || d.getUTCDay() === 6) tage.push(d.toISOString().slice(0, 10));
      d.setUTCDate(d.getUTCDate() + 1);
    }
    return tage;
  }

  const api = { GRUENDE, zufallstipp, istBeliebtesMuster, smarterTipp, auswertung,
    erwarteteVerteilung, gewinnWahrscheinlichkeit, haeufigkeiten, naechsteZiehungstage, annahmeschlussVorbei, isoDatum };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Lotto = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
