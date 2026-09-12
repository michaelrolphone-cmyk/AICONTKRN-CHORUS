// PRIME-5D-HOLO v5 — reference embedding (no deps)
// Source: Drive "--CHORUS_PRIME_HOLO_PORTABLE v5" (2025-08-20)
// Research / visualization only. Not a semantic codec. Not a crypto tool.

const cadd = ([ar, ai], [br, bi]) => [ar + br, ai + bi];
const cmul = ([ar, ai], [br, bi]) => [ar * br - ai * bi, ar * bi + ai * br];

function chi4_mod5(n) {
  const r = ((n % 5) + 5) % 5;
  switch (r) {
    case 1: return [1, 0];
    case 2: return [0, 1];
    case 3: return [0, -1];
    case 4: return [-1, 0];
    default: return [0, 0];
  }
}

function chi2_mod8(n) {
  const r = ((n % 8) + 8) % 8;
  if ((r & 1) === 0) return 0;
  return r === 1 || r === 7 ? 1 : -1;
}

function phi8_from_chars(n) {
  const z = chi4_mod5(n);
  const w = chi2_mod8(n);
  const z1 = z;
  const z2 = cmul(z1, z1);
  const z3 = cmul(z2, z1);
  const z4 = cmul(z2, z2);
  const base = [z1, z2, z3, z4];
  const v = [];
  for (let a = 0; a < 4; a++) v.push(base[a]);
  for (let a = 0; a < 4; a++) v.push([w * base[a][0], w * base[a][1]]);
  return v;
}

function buildU5x8() {
  const U = Array.from({ length: 5 }, () => Array(8));
  const norm = 1 / Math.sqrt(8);
  for (let r = 1; r <= 5; r++) {
    for (let j = 0; j < 8; j++) {
      const ang = 2 * Math.PI * r * j / 8;
      U[r - 1][j] = [Math.cos(ang) * norm, Math.sin(ang) * norm];
    }
  }
  return U;
}

function rowSumZero(U) {
  return U.every((row) => {
    const s = row.reduce((acc, z) => cadd(acc, z), [0, 0]);
    return Math.hypot(s[0], s[1]) < 1e-10;
  });
}

function mat5x8_vec8(U, v8) {
  const out = Array(5);
  for (let i = 0; i < 5; i++) {
    let acc = [0, 0];
    for (let j = 0; j < 8; j++) acc = cadd(acc, cmul(U[i][j], v8[j]));
    out[i] = acc;
  }
  return out;
}

function z5_to_R4(z5) {
  return [z5[0][0], z5[0][1], z5[1][0], z5[1][1]];
}

function linearSieve(N) {
  const lp = new Uint32Array(N + 1);
  const primes = [];
  for (let i = 2; i <= N; i++) {
    if (lp[i] === 0) {
      lp[i] = i;
      primes.push(i);
    }
    for (let j = 0; j < primes.length; j++) {
      const p = primes[j];
      const x = i * p;
      if (x > N) break;
      lp[x] = p;
      if (p === lp[i]) break;
    }
  }
  return primes;
}

function embedPrimesUpTo(N) {
  const U = buildU5x8();
  const ps = linearSieve(N);
  const out = [];
  for (const p of ps) {
    if (p <= 5) continue;
    const phi8 = phi8_from_chars(p);
    const z5 = mat5x8_vec8(U, phi8);
    out.push({ p, z5, R4: z5_to_R4(z5) });
  }
  return out;
}

const SNAP_PRIMES = [101, 103, 107, 109, 113, 127, 131];

function decodeSnapshot(primes = SNAP_PRIMES) {
  const U = buildU5x8();
  return primes.map((p, idx) => {
    const phi8 = phi8_from_chars(p);
    const z5 = mat5x8_vec8(U, phi8);
    return { idx: idx + 1, p, z5, R4: z5_to_R4(z5) };
  });
}

if (typeof require !== "undefined" && require.main === module) {
  const U = buildU5x8();
  console.log(JSON.stringify({
    row_sum_zero: rowSumZero(U),
    snapshot: decodeSnapshot().slice(0, 3),
  }));
}

module.exports = {
  chi4_mod5,
  chi2_mod8,
  phi8_from_chars,
  buildU5x8,
  rowSumZero,
  mat5x8_vec8,
  z5_to_R4,
  linearSieve,
  embedPrimesUpTo,
  decodeSnapshot,
};
