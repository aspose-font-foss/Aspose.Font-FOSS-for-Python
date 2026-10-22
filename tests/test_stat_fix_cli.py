"""Tests for stat-fix CLI command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aspose_font import FontLoader


def _run_stat_fix(input_path: str, output_path: str, dry_run: bool = False) -> tuple[int, str, str]:
    cmd = [sys.executable, "-m", "aspose_font.cli", "stat-fix", input_path, output_path]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


class TestStatFixCliDryRun:
    def test_dry_run_missing_stat(self, tmp_path: Path) -> None:
        from aspose_font import TtfFont
        from aspose_font.serializer import TtfSerializer
        from aspose_font.ttf.tables import TtfTableSet

        roboto_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(str(roboto_path))
        assert isinstance(font, TtfFont)

        has_stat = font.ttf_tables._raw.get("STAT") is not None
        if not has_stat:
            pytest.skip("Roboto test font already has STAT table")

        raw_tables = {tag: data for tag, data in font.ttf_tables._raw.items() if tag != "STAT"}
        new_tables = TtfTableSet(
            head=font.ttf_tables.head,
            hhea=font.ttf_tables.hhea,
            maxp=font.ttf_tables.maxp,
            os2=font.ttf_tables.os2,
            name=font.ttf_tables.name,
            post=font.ttf_tables.post,
            cmap=font.ttf_tables.cmap,
            loca=font.ttf_tables.loca,
            hmtx=font.ttf_tables.hmtx,
            kern=font.ttf_tables.kern,
            glyf=font.ttf_tables.glyf,
            fvar=font.ttf_tables.fvar,
            _raw=raw_tables,
        )
        modified_font = TtfFont(sfnt_data=b"", tables=new_tables, sfnt_version=font._sfnt_version)
        modified_path = tmp_path / "roboto-no-stat.ttf"
        modified_path.write_bytes(TtfSerializer.serialize(modified_font))

        output_path = tmp_path / "roboto-dry-run.ttf"
        returncode, stdout, stderr = _run_stat_fix(str(modified_path), str(output_path), dry_run=True)
        assert returncode == 0
        assert "STAT table will be synthesized" in stdout
        assert not output_path.exists()

    def test_dry_run_existing_stat(self, tmp_path: Path) -> None:
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        stat_bytes = font.get_table_bytes("STAT")
        assert stat_bytes is not None
        input_path = tmp_path / "with-stat.ttf"
        input_path.write_bytes(font.to_bytes())
        output_path = tmp_path / "with-stat-dry.ttf"
        returncode, stdout, stderr = _run_stat_fix(str(input_path), str(output_path), dry_run=True)
        assert returncode == 0
        assert "STAT table is valid" in stdout


class TestStatFixCliWrite:
    def test_write_synthesizes_stat(self, tmp_path: Path) -> None:
        from aspose_font import TtfFont
        from aspose_font.serializer import TtfSerializer
        from aspose_font.ttf.tables import TtfTableSet

        roboto_path = Path(__file__).resolve().parents[1] / "testdata" / "Roboto-VariableFont_wdth,wght.ttf"
        font = FontLoader.open(str(roboto_path))
        assert isinstance(font, TtfFont)

        has_stat = font.ttf_tables._raw.get("STAT") is not None
        if not has_stat:
            pytest.skip("Roboto test font already has STAT table")

        raw_tables = {tag: data for tag, data in font.ttf_tables._raw.items() if tag != "STAT"}
        new_tables = TtfTableSet(
            head=font.ttf_tables.head,
            hhea=font.ttf_tables.hhea,
            maxp=font.ttf_tables.maxp,
            os2=font.ttf_tables.os2,
            name=font.ttf_tables.name,
            post=font.ttf_tables.post,
            cmap=font.ttf_tables.cmap,
            loca=font.ttf_tables.loca,
            hmtx=font.ttf_tables.hmtx,
            kern=font.ttf_tables.kern,
            glyf=font.ttf_tables.glyf,
            fvar=font.ttf_tables.fvar,
            _raw=raw_tables,
        )
        modified_font = TtfFont(sfnt_data=b"", tables=new_tables, sfnt_version=font._sfnt_version)
        modified_path = tmp_path / "roboto-no-stat.ttf"
        modified_path.write_bytes(TtfSerializer.serialize(modified_font))

        output_path = tmp_path / "roboto-with-stat.ttf"
        returncode, stdout, stderr = _run_stat_fix(str(modified_path), str(output_path))
        assert returncode == 0
        assert "STAT table synthesized" in stdout
        assert output_path.exists()
        font = FontLoader.open(str(output_path))
        assert font.get_table_bytes("STAT") is not None

    def test_write_existing_stat_errors(self, tmp_path: Path) -> None:
        font = FontLoader.open("testdata/Roboto-VariableFont_wdth,wght.ttf")
        stat_bytes = font.get_table_bytes("STAT")
        assert stat_bytes is not None
        input_path = tmp_path / "with-stat.ttf"
        input_path.write_bytes(font.to_bytes())
        output_path = tmp_path / "with-stat-out.ttf"
        returncode, stdout, stderr = _run_stat_fix(str(input_path), str(output_path))
        assert returncode != 0
        assert "STAT table is valid" in stderr


class TestStatFixCliErrors:
    def test_non_variable_font_errors(self, tmp_path: Path) -> None:
        font = FontLoader.open("testdata/OpenSans-Regular.cff")
        assert not hasattr(font, "fvar") or font.fvar is None
        input_path = tmp_path / "static.ttf"
        input_path.write_bytes(font.to_bytes())
        output_path = tmp_path / "static-out.ttf"
        returncode, stdout, stderr = _run_stat_fix(str(input_path), str(output_path))
        assert returncode != 0
        assert "variable ttf font" in stderr.lower()
