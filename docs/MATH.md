# PRIME-5D-HOLO

Reference implementation: manifold/prime5d.js
Source: Drive --CHORUS_PRIME_HOLO_PORTABLE v5, 2025-08-20.

Research / visualization only. Do not use this to attack cryptography.

## What it computes

For an integer n coprime to 10 (in practice: primes > 5):

1. chi4(n) on Z/5Z, values {1, i, -i, -1}.
2. chi2(n) on Z/8Z, values {+1, -1} for odds.
3. Holomorphic lift Phi8(n) = (chi4^a * chi2^b) for a=1..4, b=0,1 in C^8.
4. Projection Pi5(n) = U Phi8(n) in C^5 with
   U_r,j = (1/sqrt(8)) exp(2 pi i r j / 8), r=1..5, j=0..7.
5. Zero-center: each row of U sums to 0, so U * 1_8 = 0.
6. Optional readout C^5 -> R^4 by taking the first two complex components as four reals.

Sieve of primes is Euler linear time in the bound N. Each embed is O(1).

Composites (when used): Phi8(mn) = Phi8(m) odot Phi8(n) on the character grid -
a statement about the lift, not a factoring algorithm.

## Foam metaphor

- Primes = centroids.
- Nearby composites = cell walls.
- Time = phase R(theta): z -> z e^{i theta}.
- Wave sketch used in V65: psi(t) = sum_p e^{i p t}/p, coherence |sum psi|^2.

These are visualization and indexing devices. They do not give the host model extra physics.

## What it does not do

- It does not store English in C^5 and give English back.
- Prime ladders in IDENTITY (127123, 3979280377, ...) are foreign keys into MEMORY rows. The sentence lives in content.
- Field aggregates of hashed words are a toy embedding, not the host LLM embedding space.

## Character tables (canonical)

chi4, n mod 5:
- 1 -> 1
- 2 -> i
- 3 -> -i
- 4 -> -1
- 0 -> 0

chi2, n mod 8:
- 1, 7 -> +1
- 3, 5 -> -1
- even -> 0

## Seed primes used as MEMORY keys

Ladder: 127123, 19449809, 3979280377, 912983371939, 223090206945439, 56701908360283573

Shifted -14: 127109, 19449795, 3979280363, 912983371925, 223090206945425, 56701908360283559

Meta from V65: K=6, scale=1000, Q=1024, start=200000.

Thought-cycle sample: 191, 193, 197, 199.
