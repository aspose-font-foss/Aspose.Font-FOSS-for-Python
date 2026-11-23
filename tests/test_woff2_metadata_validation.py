"""Unit tests for WOFF2 metadata validation (FONT-494)."""

from aspose_font.woff.woff2 import validate_woff2_metadata


def test_validate_woff2_metadata_missing_vendor_name() -> None:
    """Raises ValueError when vendor name is empty string or None."""
    metadata = {
        "vendor": {"name": "", "url": "https://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [],
    }
    try:
        validate_woff2_metadata(metadata)
        assert False, "Expected ValueError for empty vendor name"
    except ValueError as exc:
        assert "vendor.name" in str(exc).lower() or "missing" in str(exc).lower()


def test_validate_woff2_metadata_missing_copyright() -> None:
    """Raises ValueError when copyright is empty string or None."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "https://vendor.example.com"},
        "copyright": "",
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [],
    }
    try:
        validate_woff2_metadata(metadata)
        assert False, "Expected ValueError for empty copyright"
    except ValueError as exc:
        assert "copyright" in str(exc).lower() or "missing" in str(exc).lower()


def test_validate_woff2_metadata_invalid_vendor_url() -> None:
    """Raises ValueError when vendor URL lacks http/https scheme."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "ftp://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [],
    }
    try:
        validate_woff2_metadata(metadata)
        assert False, "Expected ValueError for invalid vendor URL"
    except ValueError as exc:
        assert "vendor.url" in str(exc).lower() or "url" in str(exc).lower()


def test_validate_woff2_metadata_invalid_license_url() -> None:
    """Raises ValueError when license URL lacks http/https scheme."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "https://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "mailto://license@example.com", "paragraph": "License terms"},
        "credits": [],
    }
    try:
        validate_woff2_metadata(metadata)
        assert False, "Expected ValueError for invalid license URL"
    except ValueError as exc:
        assert "license.url" in str(exc).lower() or "url" in str(exc).lower()


def test_validate_woff2_metadata_valid_metadata() -> None:
    """Completes without exception when all required fields present and URLs valid."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "https://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [{"name": "Designer", "url": "https://designer.example.com", "role": "designer"}],
    }
    validate_woff2_metadata(metadata)


def test_validate_woff2_metadata_optional_fields() -> None:
    """Accepts missing optional fields (description, credits)."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "https://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": None,
        "license": {"url": "https://example.com/license", "paragraph": None},
        "credits": [],
    }
    validate_woff2_metadata(metadata)


def test_validate_woff2_metadata_null_vendor_name() -> None:
    """Raises ValueError when vendor name is None."""
    metadata = {
        "vendor": {"name": None, "url": "https://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [],
    }
    try:
        validate_woff2_metadata(metadata)
        assert False, "Expected ValueError for None vendor name"
    except ValueError as exc:
        assert "vendor.name" in str(exc).lower() or "missing" in str(exc).lower()


def test_validate_woff2_metadata_null_copyright() -> None:
    """Raises ValueError when copyright is None."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "https://vendor.example.com"},
        "copyright": None,
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [],
    }
    try:
        validate_woff2_metadata(metadata)
        assert False, "Expected ValueError for None copyright"
    except ValueError as exc:
        assert "copyright" in str(exc).lower() or "missing" in str(exc).lower()


def test_validate_woff2_metadata_empty_vendor_url_accepted() -> None:
    """Accepts empty string vendor URL (optional field)."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": ""},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "https://example.com/license", "paragraph": "License terms"},
        "credits": [],
    }
    validate_woff2_metadata(metadata)


def test_validate_woff2_metadata_empty_license_url_accepted() -> None:
    """Accepts empty string license URL (optional field)."""
    metadata = {
        "vendor": {"name": "Test Vendor", "url": "https://vendor.example.com"},
        "copyright": "Copyright 2024",
        "description": "Test font",
        "license": {"url": "", "paragraph": "License terms"},
        "credits": [],
    }
    validate_woff2_metadata(metadata)
