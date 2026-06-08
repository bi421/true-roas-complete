#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

"""
Tests for apply_copyright and business_translator.
Pure logic — no DB or network dependencies.
"""
import pytest
from pathlib import Path

from trueroas.core.apply_copyright import (
    apply_copyright,
    HEADERS,
    COPYRIGHT_TEXT,
    IGNORE_DIRS,
)
from trueroas.core.business_translator import translate_to_business_action


# ── apply_copyright.py ────────────────────────────────────────────────────────


def test_headers_contain_copyright_text() -> None:
    for ext, header in HEADERS.items():
        assert COPYRIGHT_TEXT in header, f"Missing copyright in {ext} header"


def test_ignore_dirs_contains_git() -> None:
    assert ".git" in IGNORE_DIRS
    assert "__pycache__" in IGNORE_DIRS


def test_apply_copyright_new_file(tmp_path: Path) -> None:
    f = tmp_path / "module.py"
    f.write_text("x = 1\n", encoding="utf-8")
    apply_copyright(tmp_path)
    content = f.read_text(encoding="utf-8")
    assert COPYRIGHT_TEXT in content
    assert content.endswith("x = 1\n")


def test_apply_copyright_idempotent(tmp_path: Path) -> None:
    f = tmp_path / "module.py"
    f.write_text(HEADERS[".py"] + "x = 1\n", encoding="utf-8")
    apply_copyright(tmp_path)
    content = f.read_text(encoding="utf-8")
    # Header must appear exactly once
    assert content.count(COPYRIGHT_TEXT) == 1


def test_apply_copyright_shebang(tmp_path: Path) -> None:
    f = tmp_path / "script.py"
    f.write_text("#!/usr/bin/env python3\nprint('hi')\n", encoding="utf-8")
    apply_copyright(tmp_path)
    content = f.read_text(encoding="utf-8")
    assert content.startswith("#!/usr/bin/env python3\n")
    assert COPYRIGHT_TEXT in content


def test_apply_copyright_skips_unsupported_extension(tmp_path: Path) -> None:
    f = tmp_path / "data.json"
    original = '{"key": "value"}'
    f.write_text(original, encoding="utf-8")
    apply_copyright(tmp_path)
    assert f.read_text(encoding="utf-8") == original


def test_apply_copyright_skips_ignored_dir(tmp_path: Path) -> None:
    ignored = tmp_path / "__pycache__"
    ignored.mkdir()
    f = ignored / "cached.py"
    f.write_text("x = 1\n", encoding="utf-8")
    apply_copyright(tmp_path)
    assert COPYRIGHT_TEXT not in f.read_text(encoding="utf-8")


def test_apply_copyright_html_file(tmp_path: Path) -> None:
    f = tmp_path / "page.html"
    f.write_text("<html></html>\n", encoding="utf-8")
    apply_copyright(tmp_path)
    content = f.read_text(encoding="utf-8")
    assert COPYRIGHT_TEXT in content
    assert "<!--" in content


def test_apply_copyright_css_file(tmp_path: Path) -> None:
    f = tmp_path / "style.css"
    f.write_text("body {}\n", encoding="utf-8")
    apply_copyright(tmp_path)
    content = f.read_text(encoding="utf-8")
    assert COPYRIGHT_TEXT in content
    assert "/*" in content


def test_apply_copyright_yaml_file(tmp_path: Path) -> None:
    f = tmp_path / "config.yml"
    f.write_text("key: value\n", encoding="utf-8")
    apply_copyright(tmp_path)
    assert COPYRIGHT_TEXT in f.read_text(encoding="utf-8")


def test_apply_copyright_empty_dir(tmp_path: Path) -> None:
    # Should complete without errors on an empty directory
    apply_copyright(tmp_path)


# ── business_translator.py ───────────────────────────────────────────────────


def test_healthy_status() -> None:
    result = translate_to_business_action(
        posterior_roas=3.0,
        p10_roas=2.0,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=3.2,
        daily_spend=1000.0,
    )
    assert result["status"] == "HEALTHY"
    assert result["action_required"] == "STRONG_SCALE"
    assert result["capital_bleed_usd"] >= 0.0


def test_healthy_hold_action() -> None:
    # posterior just above break_even but not above 1.4x
    result = translate_to_business_action(
        posterior_roas=1.6,
        p10_roas=1.6,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=1.7,
        daily_spend=500.0,
    )
    assert result["status"] == "HEALTHY"
    assert result["action_required"] == "HOLD"


def test_warning_status_high_variance() -> None:
    result = translate_to_business_action(
        posterior_roas=2.0,
        p10_roas=2.0,
        break_even_roas=1.5,
        attribution_variance=0.40,
        meta_roas=3.0,
        daily_spend=1000.0,
    )
    assert result["status"] == "WARNING"
    assert result["action_required"] == "REDUCE_SPEND"


def test_warning_status_low_p10() -> None:
    result = translate_to_business_action(
        posterior_roas=2.0,
        p10_roas=1.0,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=3.0,
        daily_spend=1000.0,
    )
    assert result["status"] == "WARNING"


def test_bleeding_status() -> None:
    result = translate_to_business_action(
        posterior_roas=0.8,
        p10_roas=0.5,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=4.0,
        daily_spend=2000.0,
    )
    assert result["status"] == "BLEEDING"
    assert result["action_required"] == "PAUSE_CAMPAIGN"
    assert result["capital_bleed_usd"] > 0.0


def test_capital_bleed_zero_when_posterior_exceeds_meta() -> None:
    result = translate_to_business_action(
        posterior_roas=5.0,
        p10_roas=4.0,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=3.0,
        daily_spend=1000.0,
    )
    assert result["capital_bleed_usd"] == 0.0


def test_cfo_brief_bleeding_contains_urgent() -> None:
    result = translate_to_business_action(
        posterior_roas=0.5,
        p10_roas=0.3,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=4.0,
        daily_spend=1000.0,
    )
    assert "URGENT" in result["cfo_brief"]


def test_cfo_brief_healthy_contains_efficient() -> None:
    result = translate_to_business_action(
        posterior_roas=3.0,
        p10_roas=2.5,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=3.2,
        daily_spend=500.0,
    )
    assert "efficient" in result["cfo_brief"]


def test_return_keys_complete() -> None:
    result = translate_to_business_action(2.0, 1.5, 1.5, 0.2, 2.5, 800.0)
    assert {"status", "capital_health", "capital_bleed_usd", "action_required", "cfo_brief"} == set(result.keys())


def test_capital_bleed_precision() -> None:
    result = translate_to_business_action(
        posterior_roas=2.0,
        p10_roas=1.5,
        break_even_roas=1.5,
        attribution_variance=0.1,
        meta_roas=4.0,
        daily_spend=1000.0,
    )
    # bleed = 1000 * (4.0 - 2.0) / 4.0 = 500.0
    assert result["capital_bleed_usd"] == pytest.approx(500.0)
