# Evolving CHORUS Capabilities Locally (Self-Coding via LM Studio)

This guide outlines how to move beyond idea evolution and let `chorus evolve` propose concrete code and capability changes on a local system. The loop can already write files when the LM Studio response includes a `files` array, and the new `--context-path` option provides code context so the model can make informed edits.

## How the loop applies changes

* The evolve loop expects **only JSON** with a `desires` string and optional `files` list.
* Each file entry is `{ "path": "relative/path", "content": "..." }`.
* Paths are **relative to the desires file directory** (the base directory used for writing).
* If the desires content changes, the loop writes it and updates the ledger/state. If the desires are unchanged, it still writes any `files` provided.

## Recommended workflow for self-coding

1. **Place your desires file in the repo root** so the evolve loop can write code in the repository directory.
2. **Provide code context** using one or more `--context-path` flags so LM Studio can see the relevant files.
3. **Constrain the iteration** with `--max-iterations 1` when you want a single reviewable change per run.
4. **Use a bootstrap module** (optional) if you want to run scripted pre-steps per iteration (for example, refreshing context).

### Example command

```bash
python -m chorus evolve \
  ./CHORUS_DESIRES.md \
  ./ledger.md \
  ./state.json \
  ./session.jsonl \
  --source local \
  --model local-model \
  --api-base http://localhost:1234 \
  --max-iterations 1 \
  --context-path chorus/evolution.py \
  --context-path tests/test_evolution.py
```

## Example LM Studio response payload

```json
{
  "desires": "1) Improve evolution loop\nAdd contextual file inclusion and tests.\n",
  "files": [
    {
      "path": "chorus/evolution.py",
      "content": "# updated content here"
    },
    {
      "path": "tests/test_evolution.py",
      "content": "# updated tests here"
    }
  ]
}
```

## Tips for evolving capabilities

* **Supply the right context**: include the specific files you expect to change and any tests that should be updated.
* **Ask for tests explicitly**: the evolution prompt now instructs the model to update tests when changing code.
* **Keep changes incremental**: run one iteration at a time and review outputs.
* **Use the ledger/state outputs** to track how the system’s desires evolve alongside code changes.

## Safety notes

* The evolve loop will refuse to write outside the base directory; keep your desires file in the repo root if you want to edit project files.
* Always review and version-control the changes before deploying them.
