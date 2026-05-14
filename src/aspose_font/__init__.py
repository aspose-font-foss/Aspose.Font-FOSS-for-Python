"""Pure-Python font library for TTF, OTF, CFF, Type1, WOFF, WOFF2, and EOT."""

__version__ = "1.0.0"

from aspose_font._exceptions import (
    FontConversionException,
    FontException,
    FontNotSupportedException,
    FontParseException,
    GlyphNotFoundException,
    UnsupportedFontFormatException,
)
from aspose_font._font_base import Font, FontEncoding, FontType, GlyphAccessor
from aspose_font._types import (
    ClosePath,
    CurveTo,
    FontMetrics,
    Glyph,
    GlyphId,
    GlyphPath,
    KernPair,
    LineTo,
    MoveTo,
    PathCommand,
    QuadraticTo,
)
from aspose_font.animation import (
    AnimationAsset,
    AnimationFramePackage,
    AnimationPreset,
    AnimationPreviewBuilder,
    AnimationReviewPackage,
    AnimationShowcasePackage,
    AnimationStep,
)
from aspose_font.cff.font import CffFont
from aspose_font.cleaner import FontCleaner
from aspose_font.compatibility import (
    ActiveTupleSummary,
    CompatibilityChecker,
    CompatibilityReport,
    GlyphCompatibilityIssue,
    GlyphInterpolationIssue,
    GlyphOutlineStats,
    TupleScalarDelta,
)
from aspose_font.delta import (
    CompositeComponentMovement,
    CompositeGlyphComponent,
    DeltaInspector,
    DeltaPoint,
    DeltaTupleReport,
    GlyphDeltaComparisonReport,
    GlyphDeltaReport,
    TextDeltaComparisonReport,
    TextDeltaReport,
)
from aspose_font.eot.font import EotFont
from aspose_font.instancing import ResolvedInstance, SmartInstancer
from aspose_font.loader import FontLoader, FontSourceInfo, LoadedFont
from aspose_font.preview import FontPreviewBuilder, PreviewImage
from aspose_font.rasterizer import Rasterizer
from aspose_font.subset_presets import SUBSET_PRESETS, available_subset_presets
from aspose_font.subsetter import CoverageGroup, FontSubsetter, SubsetCoverage, SubsetResult
from aspose_font.text import GlyphLayout, TextLayout, TextRenderer
from aspose_font.ttf.font import TtfFont
from aspose_font.ttf.instancer import (
    NamingPolicyPreview,
    PlatformNamingDiagnostics,
    StatNamingDiagnostics,
)
from aspose_font.ttf.tables.fvar import AxisRecord, FvarTable, NamedInstance
from aspose_font.type1.font import Type1Font
from aspose_font.variation import (
    LocalizationCoverage,
    LocalizationResolution,
    VariableAxis,
    VariableAxisPreset,
    VariableInstance,
)
from aspose_font.web import (
    FamilyReviewExportPackage,
    WebFontAsset,
    WebFontBuilder,
    WebFontBundle,
    WebFontFamilyPackage,
)
from aspose_font.woff.woff1 import WoffFont
from aspose_font.woff.woff2 import Woff2Font

__all__ = [
    # Exceptions
    "FontException",
    "FontParseException",
    "FontConversionException",
    "FontNotSupportedException",
    "GlyphNotFoundException",
    "UnsupportedFontFormatException",
    # Enums
    "FontType",
    # ABCs
    "Font",
    "FontEncoding",
    "GlyphAccessor",
    # Value types
    "GlyphId",
    "Glyph",
    "GlyphPath",
    "FontMetrics",
    # Path commands
    "PathCommand",
    "MoveTo",
    "LineTo",
    "QuadraticTo",
    "CurveTo",
    "ClosePath",
    "KernPair",
    # Text layout
    "GlyphLayout",
    "TextLayout",
    "TextRenderer",
    "Rasterizer",
    "CoverageGroup",
    "FontSubsetter",
    "SubsetCoverage",
    "SubsetResult",
    "SUBSET_PRESETS",
    "available_subset_presets",
    "GlyphOutlineStats",
    "GlyphCompatibilityIssue",
    "GlyphInterpolationIssue",
    "ActiveTupleSummary",
    "TupleScalarDelta",
    "CompatibilityReport",
    "CompatibilityChecker",
    "CompositeGlyphComponent",
    "CompositeComponentMovement",
    "DeltaPoint",
    "DeltaTupleReport",
    "GlyphDeltaComparisonReport",
    "GlyphDeltaReport",
    "TextDeltaComparisonReport",
    "TextDeltaReport",
    "DeltaInspector",
    # Variable font
    "ResolvedInstance",
    "SmartInstancer",
    "PreviewImage",
    "FontPreviewBuilder",
    "AnimationAsset",
    "AnimationFramePackage",
    "AnimationPreset",
    "AnimationPreviewBuilder",
    "AnimationReviewPackage",
    "AnimationShowcasePackage",
    "AnimationStep",
    "AxisRecord",
    "FvarTable",
    "NamedInstance",
    "LocalizationCoverage",
    "LocalizationResolution",
    "VariableAxis",
    "VariableAxisPreset",
    "VariableInstance",
    "NamingPolicyPreview",
    "PlatformNamingDiagnostics",
    "StatNamingDiagnostics",
    "WebFontAsset",
    "WebFontBundle",
    "WebFontFamilyPackage",
    "FamilyReviewExportPackage",
    "WebFontBuilder",
    # Loader
    "FontLoader",
    "FontSourceInfo",
    "LoadedFont",
    "FontCleaner",
    # Format classes
    "TtfFont",
    "CffFont",
    "Type1Font",
    "WoffFont",
    "Woff2Font",
    "EotFont",
]
