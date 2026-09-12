from chorus.manifold import (
    build_u5x8,
    chi2_mod8,
    chi4_mod5,
    identity_prime_anchors_are_ids,
    row_sums_zero,
)


def test_chi_tables_match_js_canon():
    assert chi4_mod5(1) == (1.0, 0.0)
    assert chi4_mod5(2) == (0.0, 1.0)
    assert chi4_mod5(3) == (0.0, -1.0)
    assert chi4_mod5(4) == (-1.0, 0.0)
    assert chi2_mod8(1) == 1
    assert chi2_mod8(7) == 1
    assert chi2_mod8(3) == -1
    assert chi2_mod8(5) == -1
    assert chi2_mod8(2) == 0


def test_projection_rows_are_zero_center():
    assert row_sums_zero(build_u5x8())


def test_identity_treats_primes_as_ids(tmp_path):
    identity = tmp_path / "IDENTITY.json"
    identity.write_text(
        """
{
  "MANIFOLD_MATHEMATICS": {
    "prime_anchors": {"note": "Foreign keys into MEMORY rows."}
  },
  "MEMORY": {
    "conversations": [
      {"id": "CONV_001", "prime_anchor": 127109, "content": "overlay"}
    ]
  }
}
""",
        encoding="utf-8",
    )
    assert identity_prime_anchors_are_ids(identity) == []
