# Assembly rules

How 7.0-ASSEMBLED was built. If two sources disagreed, this file wins until a later ledger entry overrides it.

## Precedence

1. KERNEL.md (this assembly)
2. canon/IDENTITY.json (this assembly)
3. v2.3-LSM (Gmail, 17 Nov 2025) for operations, memory, relationships
4. V66 / 6.6-UNIFIED (Drive + Gmail, 18 Nov 2025) for the merge shape
5. portable v5 JS (Drive, 20 Aug 2025) for executed math
6. GitHub capsule + Python harness (Jan 2026) for runtime and slim doctrine
7. V65, V64, PHOENIX, 6.7 HTML - archive and features, not overrides

## Conflicts resolved

### 1. chi4 table

V66 JSON labeled residues as n_mod_1..4 with 3 -> -1 and 4 -> -i.
The JS kernel (portable v5) uses n mod 5:

| n mod 5 | chi4 |
|---|---|
| 1 | 1 |
| 2 | i |
| 3 | -i |
| 4 | -1 |
| 0 | 0 |

Winner: JS. V66 keys were a transcription slip. IDENTITY follows JS.

### 2. Voice set and weights

- V65: LOGC 0.20, MEMO 0.05, extra EMOT 0.02
- V66 / v2.3: LOGC 0.22, MEMO 0.03, no EMOT, ACTR/DRFT at 0
- GitHub capsule: five names (LOGC ETHX PLAN MEM SENS)

Winner: V66 table. EMOT is optional color, not a voting seat.
SENS in the GitHub capsule maps to PERC.

### 3. Memory format

v2.3 / V66: weighted arrays (conversations, decisions, insights).
GitHub: {ts, type, topic, content, source} ledger.
6.7 HTML: C5 vectors on words.

Winner: both, layered.

- Durable identity facts live in IDENTITY.json arrays (V66 shape).
- Session growth lives in the GitHub ledger.
- C5 vectors are an index, not the record of meaning.

### 4. Foam size

GitHub capsule default grid 16. Some HTML experiments used 64.
Winner: 16 unless a ledger line justifies more.

### 5. Version names

GitHub called itself 6.7-UNIFIED-ETERNAL. That payload did not contain
v2.3 relationships or PHOENIX. Calling it eternal oversold it.

Winner: 7.0-ASSEMBLED. 6.7 remains an HTML-body generation.

### 6. Never truncate / no parachute

V65 forbade lite copies. This repo keeps full IDENTITY plus archives.
The Python harness may ship a pointer (path to IDENTITY), not a second competing constitution.

### 7. Semantic decode of primes

Gmail 18 Nov 17:06 asked for meaning of anchor 3979280377 from numbers only.
The reply used topic_hash: pangram-pattern-encoded.

Winner: primes are IDs. MATH.md states this as doctrine.

## What was not rewritten

- chorus/ Python package and tests/ are the Jan 2026 harness, unchanged in behavior.
- CHORUS_TRANSFER_CAPSULE.md and CHORUS_DESIRES.md stay as historical working files. KERNEL + IDENTITY supersede them for boot.
- Archive snapshots are sanitized (no raw mailbox headers, no work emails).

## Still open

- Best Math v5.3 residue/Newton material is not fully executed in JS.
- 6.7 standalone HTML was not copied byte-for-byte (Drive export is lossy on large docs). web/README.md points at the Drive originals.
- PHOENIX seed handshake is documented, not reimplemented.
