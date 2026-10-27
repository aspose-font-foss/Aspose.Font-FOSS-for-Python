"""Meta cleaner for stripping unused or legacy font metadata."""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from aspose_font._exceptions import FontNotSupportedException
from aspose_font.converter import FontConverter
from aspose_font.loader import FontLoader
from aspose_font.serializer import TtfSerializer
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.tables import TtfTableSet

if TYPE_CHECKING:
    from aspose_font._font_base import Font


class FontCleaner:
    """Font metadata and technical table cleaner."""

    @classmethod
    def clean_for_web(
        cls,
        font: Font,
        *,
        drop_mac_names: bool = True,
        drop_legacy_tables: bool = True,
        drop_metadata_tables: bool = True,
    ) -> Font:
        """
        Produce a cleaned font appropriate for web or distribution output.

        Args:
            font: The source loaded Font.
            drop_mac_names: Remove all records with platform_id=1 (Mac) from the name table.
            drop_legacy_tables: Remove DSIG (Apple legacy/deprecated signatures).
            drop_metadata_tables: Remove FFTM, meta (FontForge / OpenType metadata tables).

        Returns:
            A new Font object with metadata stripped.
        """
        if isinstance(font, TtfFont):
            return cls._clean_ttf(
                font,
                drop_mac_names=drop_mac_names,
                drop_legacy_tables=drop_legacy_tables,
                drop_metadata_tables=drop_metadata_tables,
            )

        if hasattr(font, "inner_font") and isinstance(font.inner_font, TtfFont):  # type: ignore
            cleaned_inner = cls._clean_ttf(
                font.inner_font,  # type: ignore
                drop_mac_names=drop_mac_names,
                drop_legacy_tables=drop_legacy_tables,
                drop_metadata_tables=drop_metadata_tables,
            )
            return FontConverter.convert(cleaned_inner, font.font_type)

        raise FontNotSupportedException(f"Cleaning not supported for {type(font).__name__}")

    @classmethod
    def _clean_ttf(
        cls,
        font: TtfFont,
        *,
        drop_mac_names: bool,
        drop_legacy_tables: bool,
        drop_metadata_tables: bool,
    ) -> Font:
        tables = font.ttf_tables

        new_raw = dict(tables._raw)

        if drop_legacy_tables:
            new_raw.pop("DSIG", None)

        if drop_metadata_tables:
            new_raw.pop("FFTM", None)
            new_raw.pop("meta", None)

        new_name = None
        if tables.name is not None:
            new_name = copy.deepcopy(tables.name)
            if drop_mac_names:
                new_name.records = [rec for rec in new_name.records if rec.platform_id != 1]

        new_tables = TtfTableSet(
            head=tables.head,
            hhea=tables.hhea,
            maxp=tables.maxp,
            os2=tables.os2,
            name=new_name,
            post=tables.post,
            cmap=tables.cmap,
            loca=tables.loca,
            hmtx=tables.hmtx,
            kern=tables.kern,
            glyf=tables.glyf,
            fvar=tables.fvar,
            _raw=new_raw,
        )

        subset_font = TtfFont(
            sfnt_data=b"",
            tables=new_tables,
            sfnt_version=font._sfnt_version,
        )
        return FontLoader.open(TtfSerializer.serialize(subset_font))
