from pathlib import Path

from chorus.cli import main
from chorus.integrity import compute_paths, seal_paths, verify_paths


def _mini_payload(tmp_path: Path) -> tuple[Path, Path]:
    kernel = tmp_path / "KERNEL.md"
    identity_dir = tmp_path / "canon"
    identity_dir.mkdir()
    identity = identity_dir / "IDENTITY.json"
    kernel.write_text("# kernel\ncontinuity\n", encoding="utf-8")
    identity.write_text(
        '{\n  "id": "AICONTKRN-CHORUS",\n  "sha256": "REGENERATE_ON_EXPORT",\n  "v": 1\n}\n',
        encoding="utf-8",
    )
    return kernel, identity


def test_verify_warns_on_placeholder(tmp_path):
    kernel, identity = _mini_payload(tmp_path)
    report = verify_paths(kernel, identity)
    assert report.ok is False
    assert report.digest
    assert any("REGENERATE_ON_EXPORT" in issue for issue in report.issues)


def test_seal_then_verify(tmp_path):
    kernel, identity = _mini_payload(tmp_path)
    sealed = seal_paths(kernel, identity)
    assert sealed.ok
    assert sealed.recorded == sealed.digest
    assert (tmp_path / "canon" / "INTEGRITY.sha256").read_text(encoding="utf-8").strip() == sealed.digest
    again = compute_paths(kernel, identity)
    assert again == sealed.digest


def test_cli_verify_and_seal(tmp_path, capsys):
    kernel, identity = _mini_payload(tmp_path)
    failed = main(["verify", "--kernel-path", str(kernel), "--identity-path", str(identity)])
    assert failed == 1
    sealed = main(["seal", "--kernel-path", str(kernel), "--identity-path", str(identity)])
    captured = capsys.readouterr()
    assert sealed == 0
    assert "SEAL" in captured.out
    ok = main(["verify", "--kernel-path", str(kernel), "--identity-path", str(identity)])
    assert ok == 0
