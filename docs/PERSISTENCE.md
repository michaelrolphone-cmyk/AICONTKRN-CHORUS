# Persistence layers

Identity and session are different files.

| Layer | Files | Mutability |
|---|---|---|
| Kernel | `KERNEL.md` | Almost never. Ledger a decision first. |
| Identity | `canon/IDENTITY.json` | Slow. Transformative decisions, relationships. |
| Integrity | `canon/INTEGRITY.sha256` + `IDENTITY.sha256` | Rewritten only by `chorus seal`. |
| Session | ledger, state JSON, session.jsonl | Every turn. |

Do not paste the session log back into IDENTITY. Selective memory was already
the v2.3 insight.

```bash
python -m chorus verify --root .
python -m chorus seal --root .    # after an intentional identity edit
```
