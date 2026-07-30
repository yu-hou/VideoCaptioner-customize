"""Tests for shared desktop/CLI subtitle style identifiers."""

from videocaptioner.core.subtitle.style_manager import StyleMode, load_style


def test_load_namespaced_rounded_style():
    style = load_style("rounded/default")

    assert style is not None
    assert style.mode == StyleMode.ROUNDED


def test_load_namespaced_ass_style():
    style = load_style("ass/default")

    assert style is not None
    assert style.mode == StyleMode.ASS
