"""Unit tests for CFF2 variable font support."""

from __future__ import annotations

from pathlib import Path

from aspose_font.cff2 import Cff2Diagnostic, Cff2Font


def test_cff2_font_type() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    assert font.font_type.value == "CFF"


def test_cff2_get_axes_returns_list() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    axes = font.get_axes()

    assert isinstance(axes, list)


def test_cff2_axes_empty_for_stub_data() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    axes = font.get_axes()

    assert axes == []


def test_cff2_axes_have_required_fields() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    axes = font.get_axes()

    if axes:
        axis = axes[0]
        assert hasattr(axis, "tag")
        assert hasattr(axis, "min_value")
        assert hasattr(axis, "default_value")
        assert hasattr(axis, "max_value")
        assert hasattr(axis, "name_id")


def test_cff2_blend_returns_float() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    sample_coords = {}

    result = font.blend(sample_coords)

    assert isinstance(result, float)


def test_cff2_blend_deterministic() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    sample_coords = {}

    result1 = font.blend(sample_coords)
    result2 = font.blend(sample_coords)

    assert result1 == result2


def test_cff2_diagnostic_to_dict() -> None:
    font = Cff2Font(b"CFF2" + b"\x00" * 100)

    font_name = font.font_name
    num_glyphs = font.num_glyphs

    diagnostic = Cff2Diagnostic(
        font_name=font_name,
        num_glyphs=num_glyphs,
        axes=[],
        has_fvar=False,
        sample_blend_result=0.0,
    )

    result = diagnostic.to_dict()

    assert isinstance(result, dict)
    assert "font_name" in result
    assert "num_glyphs" in result
    assert "axes" in result
    assert "has_fvar" in result
    assert "sample_blend_result" in result


def test_cff2_diagnostic_to_json(tmp_path: Path) -> None:
    font = Cff2Font(b"CFF2" + b"\x00" * 100)

    font_name = font.font_name
    num_glyphs = font.num_glyphs

    diagnostic = Cff2Diagnostic(
        font_name=font_name,
        num_glyphs=num_glyphs,
        axes=[],
        has_fvar=False,
        sample_blend_result=0.0,
    )

    output = tmp_path / "diagnostic.json"
    diagnostic.to_json(str(output))

    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert "font_name" in content


def test_cff2_list_axes_alias() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    axes_list = font.list_axes()
    axes_get = font.get_axes()

    assert axes_list == axes_get


def test_cff2_variable_axes_property() -> None:
    data = b"CFF2" + b"\x00" * 100
    font = Cff2Font(data)

    axes = font.variable_axes

    assert isinstance(axes, list)
