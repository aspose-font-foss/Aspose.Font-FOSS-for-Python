"""OpenType DSIG (Digital Signature) table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._exceptions import FontParseException
from aspose_font._io import BinaryReader


@dataclass
class SignatureRecord:
    """A single signature record within the DSIG table."""
    signature_type: int
    length: int
    offset: int

    @classmethod
    def from_reader(cls, r: BinaryReader) -> "SignatureRecord":
        """Parse a single signature record from binary reader.

        Args:
            r: BinaryReader positioned at start of signature record.

        Returns:
            Parsed SignatureRecord instance.
        """
        signature_type = r.read_u32()
        length = r.read_u32()
        offset = r.read_u32()
        return cls(signature_type=signature_type, length=length, offset=offset)


@dataclass
class DsigTable:
    """OpenType DSIG (Digital Signature) table parser.

    Represents the Windows digital signature table (DSIG) which contains
    signature information for font integrity verification.

    Note: This parser only handles the table structure. Actual signature
    verification (certificate validation, cryptographic checks) is outside
    the scope of this library.
    """

    major_version: int
    minor_version: int
    num_styles: int
    total_length: int
    signature_records: list[SignatureRecord]
    _raw: bytes

    @classmethod
    def from_reader(cls, r: BinaryReader, length: int) -> "DsigTable":
        """Parse DSIG table from binary reader.

        Args:
            r: BinaryReader positioned at start of DSIG table.
            length: Total table length in bytes (from sfnt table directory).

        Returns:
            Parsed DsigTable instance.

        Raises:
            FontParseException: If table version is unsupported or parsing fails.
        """
        raw = r.read_bytes(length)
        rr = BinaryReader(raw)

        table_version = rr.read_u32()
        major_version = table_version >> 16
        minor_version = table_version & 0xFFFF

        # Accept both version 1.0 (correct OpenType spec) and 0.1 (common malformed format)
        if (major_version, minor_version) not in ((1, 0), (0, 1)):
            raise FontParseException(
                f"Unsupported DSIG table version: {major_version}.{minor_version}",
                format_name="TTF",
            )

        num_styles = rr.read_u16()
        total_length = rr.read_u16()

        if num_styles == 0:
            return cls(
                major_version=major_version,
                minor_version=minor_version,
                num_styles=0,
                total_length=0,
                signature_records=[],
                _raw=raw,
            )

        signature_records: list[SignatureRecord] = []
        for _ in range(num_styles):
            signature_records.append(SignatureRecord.from_reader(rr))

        return cls(
            major_version=major_version,
            minor_version=minor_version,
            num_styles=num_styles,
            total_length=total_length,
            signature_records=signature_records,
            _raw=raw,
        )

    def to_bytes(self) -> bytes:
        """Serialize DSIG table to binary data."""
        return self._raw

    def verify_checksum(self, font: object) -> bool:
        """Verify DSIG table checksum against font's checksum adjustment.

        Per the OpenType specification, the DSIG table checksum is included
        in the font's overall checksum computation. The font's head table
        contains a checksum adjustment field that should equal:

            0xB1B0AFBA - (sum of all table checksums including DSIG)

        This method validates that the DSIG table data is consistent with
        the stored checksum adjustment.

        Args:
            font: TtfFont instance containing the DSIG table.

        Returns:
            True if the DSIG table checksum is valid (matches the checksum
            adjustment stored in the font's head table), False otherwise.

        Note: This is a structural integrity check, not a cryptographic
        signature verification. It validates that the DSIG table blob has
        not been corrupted, not that the signature is cryptographically valid.
        """
        from aspose_font.serializer import TtfSerializer

        tables = font.ttf_tables
        if tables.head is None:
            return False

        dsig_bytes = tables.get_raw("DSIG")
        if dsig_bytes is None:
            return False

        try:
            sfnt_bytes = TtfSerializer.serialize(font)

            computed_sfnt_checksum = TtfSerializer._compute_table_checksum(sfnt_bytes)
            expected_adjustment = (0xB1B0AFBA - computed_sfnt_checksum) & 0xFFFFFFFF

            return expected_adjustment == tables.head.checksum_adjustment
        except Exception:
            return False
