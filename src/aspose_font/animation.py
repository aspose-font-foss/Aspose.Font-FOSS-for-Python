"""High-level animation generation helpers."""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from aspose_font._exceptions import FontNotSupportedException
from aspose_font._font_base import Font
from aspose_font.preview import (
    FontPreviewBuilder,
    PreviewImage,
    _draw_bitmap_text,
    _encode_png_rgb,
    _slugify_filename,
)
from aspose_font.rasterizer import encode_apng_from_rgb
from aspose_font.text import TextRenderer
from aspose_font.ttf.font import TtfFont

_DEFAULT_PREVIEW_TEXT = "Hamburgefons 0123456789"


@dataclass(slots=True, frozen=True)
class AnimationAsset:
    filename: str
    media_type: str
    data: bytes
    frame_count: int = 1
    fps: int = 0
    frame_labels: tuple[str, ...] = ()

    def write_to(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.data)
        return output_path


@dataclass(slots=True, frozen=True)
class AnimationFramePackage:
    directory_name: str
    storyboard: PreviewImage
    manifest_name: str
    frames: tuple[PreviewImage, ...]
    fps: int
    frame_labels: tuple[str, ...] = ()

    def write_to(self, path: str | Path) -> Path:
        output_dir = Path(path)
        output_dir.mkdir(parents=True, exist_ok=True)
        self.storyboard.write_to(output_dir / self.storyboard.filename)
        for frame in self.frames:
            frame.write_to(output_dir / frame.filename)
        manifest = {
            "fps": self.fps,
            "frame_count": len(self.frames),
            "storyboard": self.storyboard.filename,
            "frames": [
                {
                    "filename": frame.filename,
                    "label": self.frame_labels[index] if index < len(self.frame_labels) else "",
                }
                for index, frame in enumerate(self.frames)
            ],
        }
        (output_dir / self.manifest_name).write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_dir


@dataclass(slots=True, frozen=True)
class AnimationReviewPackage:
    directory_name: str
    package: AnimationFramePackage
    markdown_filename: str = "animation-review.md"
    html_filename: str = "animation-review.html"
    manifest_filename: str = "animation-review-manifest.json"
    markdown: str = ""
    html: str = ""
    manifest: dict[str, object] | None = None

    def write_to(self, path: str | Path) -> Path:
        output_dir = self.package.write_to(path)
        (output_dir / self.markdown_filename).write_text(self.markdown, encoding="utf-8")
        (output_dir / self.html_filename).write_text(self.html, encoding="utf-8")
        manifest_payload = self.manifest if self.manifest is not None else {}
        (output_dir / self.manifest_filename).write_text(
            json.dumps(manifest_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_dir


@dataclass(slots=True, frozen=True)
class AnimationShowcasePackage:
    directory_name: str
    animation: AnimationAsset
    review: AnimationReviewPackage
    html_filename: str = "animation-showcase.html"
    manifest_filename: str = "animation-showcase-manifest.json"
    html: str = ""
    manifest: dict[str, object] | None = None

    def write_to(self, path: str | Path) -> Path:
        output_dir = self.review.write_to(path)
        self.animation.write_to(output_dir / self.animation.filename)
        (output_dir / self.html_filename).write_text(self.html, encoding="utf-8")
        manifest_payload = self.manifest if self.manifest is not None else {}
        (output_dir / self.manifest_filename).write_text(
            json.dumps(manifest_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_dir


@dataclass(slots=True, frozen=True)
class AnimationPreset:
    name: str
    frames_per_segment: int
    fps: int
    size: float
    padding: int
    bounce: bool


@dataclass(slots=True, frozen=True)
class AnimationStep:
    coordinates: dict[str, float]
    label: str | None = None
    hold_frames: int = 0


_ANIMATION_PRESETS: dict[str, AnimationPreset] = {
    "draft": AnimationPreset(
        name="draft",
        frames_per_segment=8,
        fps=10,
        size=56.0,
        padding=10,
        bounce=False,
    ),
    "standard": AnimationPreset(
        name="standard",
        frames_per_segment=15,
        fps=15,
        size=72.0,
        padding=12,
        bounce=False,
    ),
    "showcase": AnimationPreset(
        name="showcase",
        frames_per_segment=24,
        fps=18,
        size=96.0,
        padding=16,
        bounce=True,
    ),
}


class AnimationPreviewBuilder:
    @classmethod
    def available_presets(cls) -> tuple[str, ...]:
        return tuple(_ANIMATION_PRESETS.keys())

    @classmethod
    def build_axis_sweep(
        cls,
        font: Font,
        axis_tag: str,
        start_val: float,
        end_val: float,
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        frames: int | None = None,
        fps: int | None = None,
        bounce: bool | None = None,
        size: float | None = None,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int | None = None,
        antialias: bool = True,
        preset: str = "standard",
        file_stem: str | None = None,
        instance_name: str | None = None,
        base_coordinates: Mapping[str, float | str] | None = None,
        easing: str = "linear",
        caption_mode: str = "labels",
    ) -> AnimationAsset:
        variable_font = _require_variable_ttf(font)
        settings = _resolve_settings(
            preset=preset,
            frames_per_segment=frames,
            fps=fps,
            size=size,
            padding=padding,
            bounce=bounce,
        )
        _ = variable_font.get_axis(axis_tag)
        if settings.frames_per_segment < 2:
            raise ValueError("Animation requires at least 2 frames")

        base_state = variable_font.smart_instancer.resolve(
            dict(base_coordinates or {}),
            instance_name=instance_name,
        ).coordinates
        values = _eased_values(start_val, end_val, settings.frames_per_segment, easing=easing)
        steps = [
            AnimationStep(
                coordinates={**base_state, axis_tag: value},
                label=f"{axis_tag}={_format_axis_value(value)}",
            )
            for value in values
        ]
        stem = file_stem or cls._default_stem(font, axis_tag)
        return cls._build_from_steps(
            variable_font,
            steps,
            text=text,
            fps=settings.fps,
            bounce=settings.bounce,
            size=settings.size,
            color=color,
            background=background,
            padding=settings.padding,
            antialias=antialias,
            file_stem=stem,
            caption_mode=caption_mode,
        )

    @classmethod
    def build_axis_sweep_package(
        cls,
        font: Font,
        axis_tag: str,
        start_val: float,
        end_val: float,
        **kwargs,
    ) -> AnimationFramePackage:
        variable_font = _require_variable_ttf(font)
        settings = _resolve_settings(
            preset=kwargs.get("preset", "standard"),
            frames_per_segment=kwargs.get("frames"),
            fps=kwargs.get("fps"),
            size=kwargs.get("size"),
            padding=kwargs.get("padding"),
            bounce=kwargs.get("bounce"),
        )
        base_state = variable_font.smart_instancer.resolve(
            dict(kwargs.get("base_coordinates") or {}),
            instance_name=kwargs.get("instance_name"),
        ).coordinates
        values = _eased_values(start_val, end_val, settings.frames_per_segment, easing=kwargs.get("easing", "linear"))
        steps = [
            AnimationStep(
                coordinates={**base_state, axis_tag: value},
                label=f"{axis_tag}={_format_axis_value(value)}",
            )
            for value in values
        ]
        stem = kwargs.get("file_stem") or cls._default_stem(font, axis_tag)
        return cls._build_frame_package_from_steps(
            variable_font,
            steps,
            text=kwargs.get("text", _DEFAULT_PREVIEW_TEXT),
            fps=settings.fps,
            bounce=settings.bounce,
            size=settings.size,
            color=kwargs.get("color", (17, 17, 17)),
            background=kwargs.get("background", (255, 253, 248)),
            padding=settings.padding,
            antialias=kwargs.get("antialias", True),
            file_stem=stem,
            caption_mode=kwargs.get("caption_mode", "labels"),
        )

    @classmethod
    def build_path(
        cls,
        font: Font,
        steps: Iterable[AnimationStep | Mapping[str, float | str]],
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        frames_per_segment: int | None = None,
        hold_frames: int = 0,
        fps: int | None = None,
        bounce: bool | None = None,
        size: float | None = None,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int | None = None,
        antialias: bool = True,
        preset: str = "standard",
        file_stem: str | None = None,
        easing: str = "linear",
        caption_mode: str = "labels",
    ) -> AnimationAsset:
        variable_font = _require_variable_ttf(font)
        settings = _resolve_settings(
            preset=preset,
            frames_per_segment=frames_per_segment,
            fps=fps,
            size=size,
            padding=padding,
            bounce=bounce,
        )
        resolved_steps = _resolve_animation_steps(variable_font, steps, hold_frames=hold_frames)
        frame_steps = _interpolate_path_steps(
            resolved_steps,
            frames_per_segment=settings.frames_per_segment,
            easing=easing,
        )
        stem = file_stem or cls._default_path_stem(font)
        return cls._build_from_steps(
            variable_font,
            frame_steps,
            text=text,
            fps=settings.fps,
            bounce=settings.bounce,
            size=settings.size,
            color=color,
            background=background,
            padding=settings.padding,
            antialias=antialias,
            file_stem=stem,
            caption_mode=caption_mode,
        )

    @classmethod
    def build_path_package(
        cls,
        font: Font,
        steps: Iterable[AnimationStep | Mapping[str, float | str]],
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        frames_per_segment: int | None = None,
        hold_frames: int = 0,
        fps: int | None = None,
        bounce: bool | None = None,
        size: float | None = None,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int | None = None,
        antialias: bool = True,
        preset: str = "standard",
        file_stem: str | None = None,
        easing: str = "linear",
        caption_mode: str = "labels",
    ) -> AnimationFramePackage:
        variable_font = _require_variable_ttf(font)
        settings = _resolve_settings(
            preset=preset,
            frames_per_segment=frames_per_segment,
            fps=fps,
            size=size,
            padding=padding,
            bounce=bounce,
        )
        resolved_steps = _resolve_animation_steps(variable_font, steps, hold_frames=hold_frames)
        frame_steps = _interpolate_path_steps(
            resolved_steps,
            frames_per_segment=settings.frames_per_segment,
            easing=easing,
        )
        stem = file_stem or cls._default_path_stem(font)
        return cls._build_frame_package_from_steps(
            variable_font,
            frame_steps,
            text=text,
            fps=settings.fps,
            bounce=settings.bounce,
            size=settings.size,
            color=color,
            background=background,
            padding=settings.padding,
            antialias=antialias,
            file_stem=stem,
            caption_mode=caption_mode,
        )

    @classmethod
    def build_path_review_package(
        cls,
        font: Font,
        steps: Iterable[AnimationStep | Mapping[str, float | str]],
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        frames_per_segment: int | None = None,
        hold_frames: int = 0,
        fps: int | None = None,
        bounce: bool | None = None,
        size: float | None = None,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int | None = None,
        antialias: bool = True,
        preset: str = "standard",
        file_stem: str | None = None,
        easing: str = "linear",
        caption_mode: str = "labels",
    ) -> AnimationReviewPackage:
        package = cls.build_path_package(
            font,
            steps,
            text=text,
            frames_per_segment=frames_per_segment,
            hold_frames=hold_frames,
            fps=fps,
            bounce=bounce,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            preset=preset,
            file_stem=file_stem,
            easing=easing,
            caption_mode=caption_mode,
        )
        context = _animation_review_context(
            package,
            text=text,
            easing=easing,
            caption_mode=caption_mode,
        )
        stem = Path(package.storyboard.filename).stem
        return AnimationReviewPackage(
            directory_name=package.directory_name,
            package=package,
            markdown_filename=f"{stem}.md",
            html_filename=f"{stem}.html",
            manifest_filename=f"{stem}-manifest.json",
            markdown=_build_animation_review_markdown(context),
            html=_build_animation_review_html(context),
            manifest=_build_animation_review_manifest(context),
        )

    @classmethod
    def build_path_showcase_package(
        cls,
        font: Font,
        steps: Iterable[AnimationStep | Mapping[str, float | str]],
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        frames_per_segment: int | None = None,
        hold_frames: int = 0,
        fps: int | None = None,
        bounce: bool | None = None,
        size: float | None = None,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int | None = None,
        antialias: bool = True,
        preset: str = "standard",
        file_stem: str | None = None,
        easing: str = "linear",
        caption_mode: str = "labels",
    ) -> AnimationShowcasePackage:
        animation = cls.build_path(
            font,
            steps,
            text=text,
            frames_per_segment=frames_per_segment,
            hold_frames=hold_frames,
            fps=fps,
            bounce=bounce,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            preset=preset,
            file_stem=file_stem,
            easing=easing,
            caption_mode=caption_mode,
        )
        review = cls.build_path_review_package(
            font,
            steps,
            text=text,
            frames_per_segment=frames_per_segment,
            hold_frames=hold_frames,
            fps=fps,
            bounce=bounce,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            preset=preset,
            file_stem=file_stem,
            easing=easing,
            caption_mode=caption_mode,
        )
        context = _animation_showcase_context(
            animation,
            review,
            text=text,
            easing=easing,
            caption_mode=caption_mode,
        )
        stem = Path(animation.filename).stem
        return AnimationShowcasePackage(
            directory_name=review.directory_name,
            animation=animation,
            review=review,
            html_filename=f"{stem}-showcase.html",
            manifest_filename=f"{stem}-showcase-manifest.json",
            html=_build_animation_showcase_html(context),
            manifest=_build_animation_showcase_manifest(context),
        )

    @classmethod
    def build_named_instance_path(
        cls,
        font: Font,
        instance_names: Iterable[str],
        *,
        text: str = _DEFAULT_PREVIEW_TEXT,
        frames_per_segment: int | None = None,
        hold_frames: int = 0,
        fps: int | None = None,
        bounce: bool | None = None,
        size: float | None = None,
        color: tuple[int, int, int] = (17, 17, 17),
        background: tuple[int, int, int] = (255, 253, 248),
        padding: int | None = None,
        antialias: bool = True,
        preset: str = "standard",
        file_stem: str | None = None,
        easing: str = "linear",
        caption_mode: str = "labels",
    ) -> AnimationAsset:
        variable_font = _require_variable_ttf(font)
        steps = [
            AnimationStep(
                coordinates=variable_font.smart_instancer.resolve(instance_name=name).coordinates,
                label=name,
            )
            for name in instance_names
        ]
        if len(steps) < 2:
            raise ValueError("Animation path requires at least two steps")
        return cls.build_path(
            variable_font,
            steps,
            text=text,
            frames_per_segment=frames_per_segment,
            hold_frames=hold_frames,
            fps=fps,
            bounce=bounce,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            preset=preset,
            file_stem=file_stem,
            easing=easing,
            caption_mode=caption_mode,
        )

    @classmethod
    def _build_from_steps(
        cls,
        font: TtfFont,
        steps: list[AnimationStep],
        *,
        text: str,
        fps: int,
        bounce: bool,
        size: float,
        color: tuple[int, int, int],
        background: tuple[int, int, int],
        padding: int,
        antialias: bool,
        file_stem: str,
        caption_mode: str,
    ) -> AnimationAsset:
        canvas_w, canvas_h, rgb_frames, frame_labels = _render_animation_frames(
            font,
            steps,
            text=text,
            fps=fps,
            bounce=bounce,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            caption_mode=caption_mode,
        )
        data = encode_apng_from_rgb(rgb_frames, canvas_w, canvas_h, fps=fps)
        return AnimationAsset(
            filename=f"{file_stem}.png",
            media_type="image/apng",
            data=data,
            frame_count=len(rgb_frames),
            fps=fps,
            frame_labels=tuple(frame_labels),
        )

    @classmethod
    def _build_frame_package_from_steps(
        cls,
        font: TtfFont,
        steps: list[AnimationStep],
        *,
        text: str,
        fps: int,
        bounce: bool,
        size: float,
        color: tuple[int, int, int],
        background: tuple[int, int, int],
        padding: int,
        antialias: bool,
        file_stem: str,
        caption_mode: str,
    ) -> AnimationFramePackage:
        canvas_w, canvas_h, rgb_frames, frame_labels = _render_animation_frames(
            font,
            steps,
            text=text,
            fps=fps,
            bounce=bounce,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            caption_mode=caption_mode,
        )
        previews = tuple(
            PreviewImage(
                filename=f"frame-{index + 1:03d}.png",
                media_type="image/png",
                data=_encode_png_rgb(canvas_w, canvas_h, rgb),
            )
            for index, rgb in enumerate(rgb_frames)
        )
        storyboard = FontPreviewBuilder.compose_sheet(
            list(previews),
            columns=min(4, len(previews)),
            labels=[label or f"Frame {index + 1}" for index, label in enumerate(frame_labels)],
            title="Animation Storyboard",
            background=background,
            file_stem=f"{file_stem}-storyboard",
        )
        return AnimationFramePackage(
            directory_name=f"{file_stem}-package",
            storyboard=storyboard,
            manifest_name="manifest.json",
            frames=previews,
            fps=fps,
            frame_labels=tuple(frame_labels),
        )

    @staticmethod
    def _default_stem(font: Font, axis_tag: str) -> str:
        family = (font.font_family or font.font_name or "preview").strip()
        stem = f"{family} sweep {axis_tag}"
        return _slugify_filename(stem)

    @staticmethod
    def _default_path_stem(font: Font) -> str:
        family = (font.font_family or font.font_name or "preview").strip()
        return _slugify_filename(f"{family} animation path")


def _render_animation_frames(
    font: TtfFont,
    steps: list[AnimationStep],
    *,
    text: str,
    fps: int,
    bounce: bool,
    size: float,
    color: tuple[int, int, int],
    background: tuple[int, int, int],
    padding: int,
    antialias: bool,
    caption_mode: str,
) -> tuple[int, int, list[bytes], list[str]]:
    del fps
    if len(steps) < 2:
        raise ValueError("Animation path requires at least two steps")
    sequence = list(steps)
    if bounce:
        sequence.extend(sequence[-2:0:-1])

    frame_layouts = []
    max_total_width = 0.0
    max_ascender = 0.0
    min_descender = 0.0

    for step in sequence:
        instanced = font.smart_instancer.instantiate(step.coordinates)
        layout = TextRenderer.layout(instanced, text, size=size, kern=True)
        frame_layouts.append((instanced, layout))
        max_total_width = max(max_total_width, layout.total_width)
        max_ascender = max(max_ascender, layout.ascender)
        min_descender = min(min_descender, layout.descender)

    canvas_w = max(1, int(math.ceil(max_total_width + 2 * padding)))
    canvas_h = max(1, int(math.ceil((max_ascender - min_descender) + 2 * padding)))

    rgb_frames: list[bytes] = []
    frame_labels: list[str] = []
    for instanced, _layout in frame_layouts:
        _w, _h, rgb = TextRenderer.render_rgb(
            instanced,
            text,
            size=size,
            color=color,
            background=background,
            padding=padding,
            antialias=antialias,
            _fixed_canvas=(canvas_w, canvas_h),
            _fixed_baseline=max_ascender,
        )
        caption = _frame_caption(sequence[len(rgb_frames)], caption_mode=caption_mode)
        rgb_frames.append(
            _apply_caption(
                rgb,
                canvas_w,
                canvas_h,
                background=background,
                caption=caption,
            )
        )
        frame_labels.append(caption)
    return canvas_w, canvas_h, rgb_frames, frame_labels


def _require_variable_ttf(font: Font) -> TtfFont:
    if not isinstance(font, TtfFont) or not font.is_variable:
        raise FontNotSupportedException("Animation sweeps require a variable TTF font")
    return font


def _resolve_settings(
    *,
    preset: str,
    frames_per_segment: int | None,
    fps: int | None,
    size: float | None,
    padding: int | None,
    bounce: bool | None,
) -> AnimationPreset:
    if preset not in _ANIMATION_PRESETS:
        available = ", ".join(AnimationPreviewBuilder.available_presets())
        raise ValueError(f"Unknown animation preset: {preset!r}. Available: {available}")
    base = _ANIMATION_PRESETS[preset]
    return AnimationPreset(
        name=base.name,
        frames_per_segment=base.frames_per_segment if frames_per_segment is None else frames_per_segment,
        fps=base.fps if fps is None else fps,
        size=base.size if size is None else size,
        padding=base.padding if padding is None else padding,
        bounce=base.bounce if bounce is None else bounce,
    )


def _resolve_animation_steps(
    font: TtfFont,
    steps: Iterable[AnimationStep | Mapping[str, float | str]],
    *,
    hold_frames: int,
) -> list[AnimationStep]:
    resolved: list[AnimationStep] = []
    for item in steps:
        if isinstance(item, AnimationStep):
            coordinates = font.smart_instancer.resolve(item.coordinates).coordinates
            resolved.append(
                AnimationStep(
                    coordinates=coordinates,
                    label=item.label,
                    hold_frames=max(0, item.hold_frames),
                )
            )
            continue
        coordinates = font.smart_instancer.resolve(dict(item)).coordinates
        resolved.append(
            AnimationStep(
                coordinates=coordinates,
                hold_frames=max(0, hold_frames),
            )
        )
    if len(resolved) < 2:
        raise ValueError("Animation path requires at least two steps")
    return resolved


def _interpolate_path_steps(
    steps: list[AnimationStep],
    *,
    frames_per_segment: int,
    easing: str,
) -> list[AnimationStep]:
    if frames_per_segment < 2:
        raise ValueError("Animation path requires at least 2 frames per segment")
    easing_fn = _resolve_easing(easing)
    output: list[AnimationStep] = []
    for index in range(len(steps) - 1):
        before = steps[index]
        after = steps[index + 1]
        axis_tags = sorted(set(before.coordinates) | set(after.coordinates))
        start = {tag: float(before.coordinates.get(tag, 0.0)) for tag in axis_tags}
        end = {tag: float(after.coordinates.get(tag, 0.0)) for tag in axis_tags}
        for frame_index in range(frames_per_segment):
            if index > 0 and frame_index == 0:
                continue
            raw_t = frame_index / (frames_per_segment - 1)
            t = easing_fn(raw_t)
            label = after.label if frame_index == frames_per_segment - 1 else before.label
            output.append(
                AnimationStep(
                    coordinates={
                        tag: start[tag] + (end[tag] - start[tag]) * t
                        for tag in axis_tags
                    },
                    label=label,
                )
            )
        output.extend(
            AnimationStep(coordinates=dict(after.coordinates), label=after.label)
            for _ in range(after.hold_frames)
        )
    return output


def _resolve_easing(name: str):
    normalized = name.strip().lower()
    easing_map = {
        "linear": lambda t: t,
        "ease-in": lambda t: t * t,
        "ease-out": lambda t: 1.0 - (1.0 - t) * (1.0 - t),
        "ease-in-out": lambda t: 2.0 * t * t if t < 0.5 else 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0,
    }
    if normalized not in easing_map:
        available = ", ".join(sorted(easing_map))
        raise ValueError(f"Unknown animation easing: {name!r}. Available: {available}")
    return easing_map[normalized]


def _frame_caption(step: AnimationStep, *, caption_mode: str) -> str:
    normalized = caption_mode.strip().lower()
    if normalized == "none":
        return ""
    coordinates = _coordinate_label(step.coordinates)
    label = step.label or coordinates
    if normalized == "labels":
        return label
    if normalized == "coordinates":
        return coordinates
    if normalized == "both":
        return label if label == coordinates else f"{label} | {coordinates}"
    available = "none, labels, coordinates, both"
    raise ValueError(f"Unknown animation caption mode: {caption_mode!r}. Available: {available}")


def _coordinate_label(coordinates: Mapping[str, float]) -> str:
    return ", ".join(
        f"{tag}={_format_axis_value(float(value))}"
        for tag, value in sorted(coordinates.items())
    )


def _apply_caption(
    rgb: bytes,
    width: int,
    height: int,
    *,
    background: tuple[int, int, int],
    caption: str,
) -> bytes:
    if not caption:
        return rgb
    pixels = bytearray(rgb)
    text = caption.upper()
    box_height = 14
    _fill_rect(
        pixels,
        width,
        0,
        0,
        width,
        box_height,
        background,
    )
    _draw_bitmap_text(pixels, width, 6, 3, text[: max(1, (width - 12) // 6)], color=(68, 60, 50))
    return bytes(pixels)


def _fill_rect(
    pixels: bytearray,
    width: int,
    left: int,
    top: int,
    rect_width: int,
    rect_height: int,
    color: tuple[int, int, int],
) -> None:
    canvas_height = len(pixels) // (width * 3)
    start_x = max(0, left)
    end_x = min(width, left + rect_width)
    start_y = max(0, top)
    end_y = min(canvas_height, top + rect_height)
    if end_x <= start_x or end_y <= start_y:
        return
    for y in range(start_y, end_y):
        row_start = (y * width + start_x) * 3
        row_end = (y * width + end_x) * 3
        row = bytearray()
        for _ in range(end_x - start_x):
            row.extend(color)
        pixels[row_start:row_end] = row


def _linspace(start: float, end: float, count: int) -> list[float]:
    if count < 2:
        raise ValueError("Animation requires at least 2 frames")
    step = (end - start) / (count - 1)
    return [start + step * index for index in range(count)]


def _eased_values(start: float, end: float, count: int, *, easing: str) -> list[float]:
    values = _linspace(0.0, 1.0, count)
    easing_fn = _resolve_easing(easing)
    return [start + (end - start) * easing_fn(value) for value in values]


def _format_axis_value(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".") or "0"


def _animation_review_context(
    package: AnimationFramePackage,
    *,
    text: str,
    easing: str,
    caption_mode: str,
) -> dict[str, object]:
    return {
        "directory_name": package.directory_name,
        "storyboard_filename": package.storyboard.filename,
        "frame_count": len(package.frames),
        "fps": package.fps,
        "text": text,
        "easing": easing,
        "caption_mode": caption_mode,
        "frames": [
            {
                "filename": frame.filename,
                "label": package.frame_labels[index] if index < len(package.frame_labels) else "",
            }
            for index, frame in enumerate(package.frames)
        ],
    }


def _build_animation_review_markdown(context: dict[str, object]) -> str:
    frames = context["frames"]
    lines = [
        "# Animation Review Package",
        "",
        f"- Preview text: `{context['text']}`",
        f"- FPS: `{context['fps']}`",
        f"- Frame count: `{context['frame_count']}`",
        f"- Easing: `{context['easing']}`",
        f"- Caption mode: `{context['caption_mode']}`",
        f"- Storyboard: `{context['storyboard_filename']}`",
        "",
        "## Frames",
        "",
    ]
    for index, frame in enumerate(frames, start=1):
        lines.append(f"{index}. `{frame['filename']}` - {frame['label'] or 'Unlabeled'}")
    lines.append("")
    return "\n".join(lines)


def _build_animation_review_html(context: dict[str, object]) -> str:
    items = []
    for frame in context["frames"]:
        items.append(
            "      <li>"
            f"<strong>{html.escape(str(frame['filename']))}</strong>"
            f" - {html.escape(str(frame['label'] or 'Unlabeled'))}"
            "</li>"
        )
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "  <title>Animation Review Package</title>\n"
        "  <style>body{font-family:Georgia,serif;max-width:960px;margin:32px auto;padding:0 20px;color:#2a241c;background:#fffdf8} img{max-width:100%;height:auto;border:1px solid #d7c7b1} code{background:#f4eee5;padding:1px 4px} li{margin:6px 0}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Animation Review Package</h1>\n"
        f"  <p><strong>Preview text:</strong> {html.escape(str(context['text']))}</p>\n"
        f"  <p><strong>FPS:</strong> {context['fps']} | <strong>Frames:</strong> {context['frame_count']} | <strong>Easing:</strong> {html.escape(str(context['easing']))} | <strong>Caption mode:</strong> {html.escape(str(context['caption_mode']))}</p>\n"
        f"  <p><strong>Storyboard:</strong> <code>{html.escape(str(context['storyboard_filename']))}</code></p>\n"
        f"  <p><img src=\"{html.escape(str(context['storyboard_filename']))}\" alt=\"Animation storyboard\"></p>\n"
        "  <h2>Frames</h2>\n"
        "  <ol>\n"
        f"{chr(10).join(items)}\n"
        "  </ol>\n"
        "</body>\n"
        "</html>\n"
    )


def _build_animation_review_manifest(context: dict[str, object]) -> dict[str, object]:
    return {
        "type": "animation-review-package",
        "storyboard": context["storyboard_filename"],
        "text": context["text"],
        "fps": context["fps"],
        "frame_count": context["frame_count"],
        "easing": context["easing"],
        "caption_mode": context["caption_mode"],
        "frames": list(context["frames"]),
    }


def _animation_showcase_context(
    animation: AnimationAsset,
    review: AnimationReviewPackage,
    *,
    text: str,
    easing: str,
    caption_mode: str,
) -> dict[str, object]:
    review_manifest = review.manifest if review.manifest is not None else {}
    return {
        "animation_filename": animation.filename,
        "animation_media_type": animation.media_type,
        "frame_count": animation.frame_count,
        "fps": animation.fps,
        "frame_labels": list(animation.frame_labels),
        "text": text,
        "easing": easing,
        "caption_mode": caption_mode,
        "review_html_filename": review.html_filename,
        "review_markdown_filename": review.markdown_filename,
        "review_manifest_filename": review.manifest_filename,
        "review_manifest": review_manifest,
        "storyboard_filename": review_manifest.get("storyboard", ""),
    }


def _build_animation_showcase_html(context: dict[str, object]) -> str:
    frame_labels = context["frame_labels"]
    items = []
    for index, label in enumerate(frame_labels, start=1):
        items.append(
            "      <li>"
            f"<strong>Frame {index}</strong>: {html.escape(str(label or 'Unlabeled'))}"
            "</li>"
        )
    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "  <meta charset=\"utf-8\">\n"
        "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "  <title>Animation Showcase</title>\n"
        "  <style>body{font-family:Georgia,serif;max-width:1040px;margin:32px auto;padding:0 20px;color:#2a241c;background:#fffdf8} img{max-width:100%;height:auto;border:1px solid #d7c7b1} .hero{display:grid;gap:20px}.panel{background:#fff8f0;border:1px solid #d7c7b1;padding:16px} code{background:#f4eee5;padding:1px 4px} li{margin:6px 0}</style>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Animation Showcase</h1>\n"
        f"  <p><strong>Preview text:</strong> {html.escape(str(context['text']))}</p>\n"
        f"  <p><strong>FPS:</strong> {context['fps']} | <strong>Frames:</strong> {context['frame_count']} | <strong>Easing:</strong> {html.escape(str(context['easing']))} | <strong>Caption mode:</strong> {html.escape(str(context['caption_mode']))}</p>\n"
        "  <div class=\"hero\">\n"
        "    <div class=\"panel\">\n"
        "      <h2>Animated Preview</h2>\n"
        f"      <img src=\"{html.escape(str(context['animation_filename']))}\" alt=\"Animation preview\">\n"
        "    </div>\n"
        "    <div class=\"panel\">\n"
        "      <h2>Storyboard</h2>\n"
        f"      <img src=\"{html.escape(str(context['storyboard_filename']))}\" alt=\"Animation storyboard\">\n"
        "    </div>\n"
        "  </div>\n"
        "  <h2>Frame Labels</h2>\n"
        "  <ol>\n"
        f"{chr(10).join(items)}\n"
        "  </ol>\n"
        "  <h2>Review Files</h2>\n"
        f"  <p><a href=\"{html.escape(str(context['review_html_filename']))}\">Review HTML</a> | <a href=\"{html.escape(str(context['review_markdown_filename']))}\">Review Markdown</a> | <a href=\"{html.escape(str(context['review_manifest_filename']))}\">Review Manifest</a></p>\n"
        "</body>\n"
        "</html>\n"
    )


def _build_animation_showcase_manifest(context: dict[str, object]) -> dict[str, object]:
    return {
        "type": "animation-showcase-package",
        "animation": {
            "filename": context["animation_filename"],
            "media_type": context["animation_media_type"],
            "fps": context["fps"],
            "frame_count": context["frame_count"],
            "frame_labels": list(context["frame_labels"]),
        },
        "text": context["text"],
        "easing": context["easing"],
        "caption_mode": context["caption_mode"],
        "storyboard": context["storyboard_filename"],
        "review_html": context["review_html_filename"],
        "review_markdown": context["review_markdown_filename"],
        "review_manifest": context["review_manifest_filename"],
    }


__all__ = [
    "AnimationAsset",
    "AnimationFramePackage",
    "AnimationReviewPackage",
    "AnimationShowcasePackage",
    "AnimationPreset",
    "AnimationPreviewBuilder",
    "AnimationStep",
]
