"""Tests for device-metrics CLI command (FONT-513)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aspose_font._io import BinaryWriter
from aspose_font.ttf.tables.hdmx import HdmxRecord, HdmxTable, VdmxGroup, VdmxTable

CLI = [sys.executable, "-m", "aspose_font.cli"]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        CLI + list(args),
        capture_output=True,
        text=True,
    )


def _build_hdmx_bytes(hdmx: HdmxTable) -> bytes:
    """Build binary hdmx table from HdmxTable object."""
    bw = BinaryWriter()
    bw.write_u16(hdmx.version)
    bw.write_u16(hdmx.num_records)
    bw.write_u32(hdmx.size_device_record)
    for record in hdmx.records:
        bw.write_u8(record.pixel_size)
        bw.write_u8(len(record.widths))
        for width in record.widths:
            bw.write_i8(width)
    return bw.to_bytes()


def _build_vdmx_bytes(vdmx: VdmxTable) -> bytes:
    """Build binary vdmx table from VdmxTable object."""
    bw = BinaryWriter()
    bw.write_u16(vdmx.version)
    bw.write_u16(vdmx.num_recs)
    bw.write_u8(vdmx.num_ratios)
    bw.write_u8(0)
    bw.write_u16(12)
    bw.write_u16(1)
    bw.write_u16(0)
    for ratio in vdmx.ratio_range_table:
        bw.write_u8(ratio["aspect_ratio"])
        bw.write_u8(ratio["start_ratio"])
        bw.write_u8(ratio["end_ratio"])
        bw.write_u8(ratio["range_start"])
        bw.write_u8(ratio["range_end"])
    for group in vdmx.groups:
        bw.write_u8(group.y_pel_height)
        bw.write_i16(group.y_max)
        bw.write_i16(group.y_min)
    return bw.to_bytes()


def create_font_with_device_metrics(
    tmp_path: Path, hdmx: HdmxTable | None, vdmx: VdmxTable | None
) -> Path:
    """Create minimal TTF with optional device metrics tables."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)

    tables: list[tuple[bytes, str]] = []

    if hdmx is not None:
        hdmx_bytes = _build_hdmx_bytes(hdmx)
        tables.append((hdmx_bytes, "hdmx"))

    if vdmx is not None:
        vdmx_bytes = _build_vdmx_bytes(vdmx)
        tables.append((vdmx_bytes, "VDMX"))

    num_tables = 2 + len(tables)
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )

    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)

    directory = b""
    directory += b"head" + (0).to_bytes(4, "big") + head_offset.to_bytes(4, "big") + len(head).to_bytes(4, "big")
    directory += b"maxp" + (0).to_bytes(4, "big") + maxp_offset.to_bytes(4, "big") + len(maxp).to_bytes(4, "big")

    current_offset = maxp_offset + len(maxp)
    for table_bytes, table_tag in tables:
        table_offset = current_offset
        current_offset += len(table_bytes)
        directory += table_tag.encode() + (0).to_bytes(4, "big") + table_offset.to_bytes(4, "big") + len(table_bytes).to_bytes(4, "big")

    minimal_ttf = offset_table + directory + head + maxp
    for table_bytes, _ in tables:
        minimal_ttf += table_bytes

    font_path = tmp_path / "device-metrics-font.ttf"
    font_path.write_bytes(minimal_ttf)
    return font_path


def test_device_metrics_command_prints_summary(tmp_path: Path) -> None:
    """Test that device-metrics prints summary for font with device metrics tables."""
    hdmx = HdmxTable(
        version=0x0001,
        num_records=2,
        size_device_record=8,
        records=[
            HdmxRecord(pixel_size=12, widths=[100, 120, 80]),
            HdmxRecord(pixel_size=14, widths=[110, 125, 90]),
        ],
    )
    vdmx = VdmxTable(
        version=0x0001,
        num_recs=2,
        num_ratios=1,
        ratio_range_table=[{"aspect_ratio": 50, "start_ratio": 50, "end_ratio": 50, "range_start": 10, "range_end": 20}],
        groups=[
            VdmxGroup(y_pel_height=10, y_max=800, y_min=-200),
            VdmxGroup(y_pel_height=20, y_max=900, y_min=-150),
        ],
    )
    font_path = create_font_with_device_metrics(tmp_path, hdmx, vdmx)
    result = run("device-metrics", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "hdmx table:" in out
    assert "VDMX table:" in out
    assert "Available PPEM values:" in out
    assert "[12, 14]" in out


def test_device_metrics_accepts_ppem_filter(tmp_path: Path) -> None:
    """Test that --ppem filters output to a specific pixel size."""
    hdmx = HdmxTable(
        version=0x0001,
        num_records=2,
        size_device_record=8,
        records=[
            HdmxRecord(pixel_size=10, widths=[100, 120, 80]),
            HdmxRecord(pixel_size=20, widths=[110, 125, 90]),
        ],
    )
    vdmx = VdmxTable(
        version=0x0001,
        num_recs=2,
        num_ratios=1,
        ratio_range_table=[{"aspect_ratio": 50, "start_ratio": 50, "end_ratio": 50, "range_start": 10, "range_end": 20}],
        groups=[
            VdmxGroup(y_pel_height=10, y_max=800, y_min=-200),
            VdmxGroup(y_pel_height=20, y_max=900, y_min=-150),
        ],
    )
    font_path = create_font_with_device_metrics(tmp_path, hdmx, vdmx)
    result = run("device-metrics", str(font_path), "--ppem", "10")
    assert result.returncode == 0
    out = result.stdout
    assert "PPEM 10:" in out
    assert "max_width=120" in out
    assert "min_width=80" in out
    assert "y_max=800" in out
    assert "y_min=-200" in out


def test_device_metrics_accepts_json_output_flag(tmp_path: Path) -> None:
    """Test that --json-output writes valid JSON report for font with device metrics."""
    hdmx = HdmxTable(
        version=0x0001,
        num_records=1,
        size_device_record=4,
        records=[HdmxRecord(pixel_size=12, widths=[100])],
    )
    vdmx = VdmxTable(
        version=0x0001,
        num_recs=1,
        num_ratios=1,
        ratio_range_table=[{"aspect_ratio": 50, "start_ratio": 50, "end_ratio": 50, "range_start": 10, "range_end": 20}],
        groups=[VdmxGroup(y_pel_height=10, y_max=800, y_min=-200)],
    )
    font_path = create_font_with_device_metrics(tmp_path, hdmx, vdmx)
    json_path = tmp_path / "device-metrics.json"
    result = run("device-metrics", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    assert json_path.exists()
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert "hdmx" in data
    assert "vdmx" in data
    assert data["hdmx"] is not None
    assert data["vdmx"] is not None
    assert "table" in data["hdmx"]
    assert data["hdmx"]["table"]["version"] == "1"


def test_device_metrics_handles_font_without_device_metrics_exits_0(tmp_path: Path) -> None:
    """Test that fonts without device metrics tables print notice and exit 0."""
    head = bytes(12) + (0x5F0F3CF5).to_bytes(4, "big") + bytes(54 - 16)
    maxp = (0x00010000).to_bytes(4, "big") + (1).to_bytes(2, "big") + bytes(26)
    num_tables = 2
    offset_table = (
        b"\x00\x01\x00\x00"
        + num_tables.to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
        + (0).to_bytes(2, "big")
    )
    head_offset = 12 + num_tables * 16
    maxp_offset = head_offset + len(head)
    directory = (
        b"head"
        + (0).to_bytes(4, "big")
        + head_offset.to_bytes(4, "big")
        + len(head).to_bytes(4, "big")
        + b"maxp"
        + (0).to_bytes(4, "big")
        + maxp_offset.to_bytes(4, "big")
        + len(maxp).to_bytes(4, "big")
    )
    minimal_ttf = offset_table + directory + head + maxp
    font_path = tmp_path / "no-device-metrics.ttf"
    font_path.write_bytes(minimal_ttf)

    result = run("device-metrics", str(font_path))
    assert result.returncode == 0
    assert "hdmx table: Not present" in result.stdout
    assert "VDMX table: Not present" in result.stdout
    assert "Note:" in result.stdout


def test_device_metrics_non_ttf_font_exits_with_error() -> None:
    """Test that non-TTF fonts produce error."""
    pfb_path = str(Path(__file__).resolve().parents[1] / "testdata" / "OpenSans-Regular.pfb")
    result = run("device-metrics", pfb_path)
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "device-metrics inspection is only supported" in combined_output


def test_device_metrics_json_output_contains_expected_structure(tmp_path: Path) -> None:
    """Test that JSON output has expected structure for font with device metrics."""
    hdmx = HdmxTable(
        version=0x0001,
        num_records=2,
        size_device_record=8,
        records=[
            HdmxRecord(pixel_size=12, widths=[100, 120, 80]),
            HdmxRecord(pixel_size=14, widths=[110, 125, 90]),
        ],
    )
    vdmx = VdmxTable(
        version=0x0001,
        num_recs=2,
        num_ratios=1,
        ratio_range_table=[{"aspect_ratio": 50, "start_ratio": 50, "end_ratio": 50, "range_start": 10, "range_end": 20}],
        groups=[
            VdmxGroup(y_pel_height=10, y_max=800, y_min=-200),
            VdmxGroup(y_pel_height=20, y_max=900, y_min=-150),
        ],
    )
    font_path = create_font_with_device_metrics(tmp_path, hdmx, vdmx)
    json_path = tmp_path / "device-metrics.json"
    result = run("device-metrics", str(font_path), "--json-output", str(json_path))
    assert result.returncode == 0
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data["hdmx"], dict)
    assert "table" in data["hdmx"]
    assert "num_records" in data["hdmx"]["table"]
    assert isinstance(data["hdmx"]["table"]["num_records"], int)
    assert "available_ppem" in data["hdmx"]
    assert isinstance(data["hdmx"]["available_ppem"], list)
    assert data["hdmx"]["available_ppem"] == [12, 14]
    assert isinstance(data["vdmx"], dict)
    assert "table" in data["vdmx"]
    assert "group_count" in data["vdmx"]
    assert isinstance(data["vdmx"]["group_count"], int)
    assert data["vdmx"]["table"]["version"] == "1"


def test_device_metrics_ppem_not_available_exits_error(tmp_path: Path) -> None:
    """Test that --ppem with non-existent value produces error."""
    hdmx = HdmxTable(
        version=0x0001,
        num_records=2,
        size_device_record=8,
        records=[
            HdmxRecord(pixel_size=12, widths=[100, 120, 80]),
            HdmxRecord(pixel_size=14, widths=[110, 125, 90]),
        ],
    )
    vdmx = VdmxTable(
        version=0x0001,
        num_recs=0,
        num_ratios=0,
        ratio_range_table=[],
        groups=[],
    )
    font_path = create_font_with_device_metrics(tmp_path, hdmx, vdmx)
    result = run("device-metrics", str(font_path), "--ppem", "99")
    assert result.returncode != 0
    combined_output = result.stdout + result.stderr
    assert "not available" in combined_output


def test_device_metrics_hdmx_only(tmp_path: Path) -> None:
    """Test that device-metrics works with only hdmx table."""
    hdmx = HdmxTable(
        version=0x0001,
        num_records=1,
        size_device_record=4,
        records=[HdmxRecord(pixel_size=12, widths=[100])],
    )
    font_path = create_font_with_device_metrics(tmp_path, hdmx, None)
    result = run("device-metrics", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "hdmx table:" in out
    assert "VDMX table: Not present" in out


def test_device_metrics_vdmx_only(tmp_path: Path) -> None:
    """Test that device-metrics works with only vdmx table."""
    vdmx = VdmxTable(
        version=0x0001,
        num_recs=1,
        num_ratios=1,
        ratio_range_table=[{"aspect_ratio": 50, "start_ratio": 50, "end_ratio": 50, "range_start": 10, "range_end": 20}],
        groups=[VdmxGroup(y_pel_height=10, y_max=800, y_min=-200)],
    )
    font_path = create_font_with_device_metrics(tmp_path, None, vdmx)
    result = run("device-metrics", str(font_path))
    assert result.returncode == 0
    out = result.stdout
    assert "hdmx table: Not present" in out
    assert "VDMX table:" in out
    assert "Number of VDMX groups:" in out
