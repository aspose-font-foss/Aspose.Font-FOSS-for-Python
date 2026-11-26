"""CPAL table parser."""

from __future__ import annotations

from dataclasses import dataclass

from aspose_font._io import BinaryReader


@dataclass(slots=True)
class ColorPalette:
    colors: list[tuple[int, int, int, int]]

    def __len__(self) -> int:
        return len(self.colors)

    def __getitem__(self, index: int) -> tuple[int, int, int, int]:
        return self.colors[index]


@dataclass(slots=True)
class CpalTable:
    version: int
    num_palettes: int
    num_color_records: int
    color_record_indices: list[int]
    palettes: list[ColorPalette]
    palette_labels: list[int]
    color_labels: list[int]

    @classmethod
    def from_reader(cls, r: BinaryReader, table_length: int, *, num_palette_colors: int | None = None) -> "CpalTable":
        version = r.read_u16()
        num_palettes = r.read_u16()
        num_color_records = r.read_u16()

        initial_offset = r.tell()
        color_record_array_offset = initial_offset + num_palettes * 4

        color_record_indices: list[int] = []
        for _ in range(num_palettes):
            color_record_indices.append(r.read_u32())

        palettes: list[ColorPalette] = []
        num_colors = num_palette_colors if num_palette_colors is not None else (num_color_records // num_palettes if num_palettes > 0 else 0)
        for color_record_index in color_record_indices:
            r.seek(color_record_array_offset + color_record_index)
            colors: list[tuple[int, int, int, int]] = []
            for _ in range(num_colors):
                if version == 0:
                    blue = r.read_u8()
                    green = r.read_u8()
                    red = r.read_u8()
                    zero = r.read_u8()
                    colors.append((red, green, blue, zero))
                else:
                    red = r.read_u8()
                    green = r.read_u8()
                    blue = r.read_u8()
                    alpha = r.read_u8()
                    colors.append((red, green, blue, alpha))
            palettes.append(ColorPalette(colors=colors))

        palette_labels: list[int] = []
        color_labels: list[int] = []
        if version >= 1:
            header_size = 6
            indices_size = num_palettes * 4
            colors_data_size = num_colors * num_palettes * 4
            expected_labels_offset = header_size + indices_size + colors_data_size

            if expected_labels_offset + 4 <= table_length:
                r.seek(expected_labels_offset)
                palette_label_offset = r.read_u16()
                color_label_offset = r.read_u16()

                if palette_label_offset != 0 and palette_label_offset < table_length:
                    r.seek(initial_offset + palette_label_offset)
                    for _ in range(num_palettes):
                        label = r.read_u16()
                        palette_labels.append(label)

                if color_label_offset != 0 and color_label_offset < table_length:
                    r.seek(initial_offset + color_label_offset)
                    for _ in range(num_color_records):
                        label = r.read_u16()
                        color_labels.append(label)

        return cls(
            version=version,
            num_palettes=num_palettes,
            num_color_records=num_color_records,
            color_record_indices=color_record_indices,
            palettes=palettes,
            palette_labels=palette_labels,
            color_labels=color_labels
        )
