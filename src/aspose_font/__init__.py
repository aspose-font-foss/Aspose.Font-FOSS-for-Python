"""Pure-Python font library for TTF, OTF, CFF, Type1, WOFF, WOFF2, and EOT."""
# ruff: noqa: I001

try:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("aspose-font-foss")
    except PackageNotFoundError:
        __version__ = version("aspose-font")
except (PackageNotFoundError, ImportError):
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
from aspose_font.autonomous import (
    AutonomousWorkflowDecision,
    AutonomousWorkflowResult,
    analyze_font_for_autonomous_workflow,
    run_autonomous_workflow,
    run_autonomous_workflow_from_path,
)
from aspose_font.autonomous_dev import run_autonomous_development
from aspose_font.capability import (
    AxisDescription,
    CapabilitySummary,
    CSSHints,
    FontCapabilityBuilder,
    FontCapabilityReport,
    ReleaseRisk,
    ScriptCoverage,
)
from aspose_font.cff.font import CffFont
from aspose_font.cff2.font import Cff2Font
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
from aspose_font.corpus_manifest import CorpusManifest, FixtureEntry
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
from aspose_font.diagnostics.coverage import (
    compute_designspace_coverage,
    generate_designspace_coverage_report,
)
from aspose_font.eot.font import EotFont
from aspose_font.instances import VariableInstanceBuilder, VariableInstancePackage
from aspose_font.instancing import ResolvedInstance, SmartInstancer
from aspose_font.loader import FontLoader, FontSourceInfo, LoadedFont
from aspose_font.utils import extract_font_metadata
from aspose_font.optimizer import (
    WebFontOptimizerDecision,
    WebFontOptimizerPackageWithDecision,
    analyze_font_for_web_optimization,
    build_web_optimizer_package,
    build_web_optimizer_package_with_plan,
)
from aspose_font.performance import (
    PerformanceBaselineReport,
    PerformanceBenchmark,
    PerformanceMeasurement,
    PerformanceRegressionPackage,
    PerformanceReport,
    PerformanceResult,
)
from aspose_font.preview import FontPreviewBuilder, PreviewImage, generate_waterfall_matrix
from aspose_font.qa import FontQaPackage, FontQaReport, FontQaReporter, generate_decision_report
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
    LanguageProfile,
    LocalizationCoverage,
    LocalizationResolution,
    RequestedLanguageHint,
    VariableAxis,
    VariableAxisPreset,
    VariableInstance,
    build_language_profiles,
)
from aspose_font.visual_proof import run_visual_proof
from aspose_font.web import (
    FamilyReviewExportPackage,
    WebFontAsset,
    WebFontBuilder,
    WebFontBundle,
    WebFontFamilyPackage,
    WebFontOptimizer,
    WebFontOptimizerPackage,
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
    # Corpus manifest
    "CorpusManifest",
    "FixtureEntry",
    # Diagnostics
    "compute_designspace_coverage",
    "generate_designspace_coverage_report",
    # Visual proofing
    "run_visual_proof",
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
    "generate_waterfall_matrix",
    "FontQaPackage",
    "FontQaReport",
    "FontQaReporter",
    "generate_decision_report",
    "AnimationAsset",
    "AnimationFramePackage",
    "AnimationPreset",
    "AnimationPreviewBuilder",
    "AnimationReviewPackage",
    "AnimationShowcasePackage",
    "AnimationStep",
    "AutonomousWorkflowDecision",
    "AutonomousWorkflowResult",
    "analyze_font_for_autonomous_workflow",
    "run_autonomous_workflow",
    "run_autonomous_workflow_from_path",
    "run_autonomous_development",
    "AxisRecord",
    "FvarTable",
    "NamedInstance",
    "LocalizationCoverage",
    "LocalizationResolution",
    "RequestedLanguageHint",
    "LanguageProfile",
    "build_language_profiles",
    "VariableAxis",
    "VariableAxisPreset",
    "VariableInstance",
    "VariableInstanceBuilder",
    "VariableInstancePackage",
    "NamingPolicyPreview",
    "PlatformNamingDiagnostics",
    "StatNamingDiagnostics",
    "WebFontAsset",
    "WebFontBundle",
    "WebFontFamilyPackage",
    "WebFontOptimizer",
    "WebFontOptimizerPackage",
    "FamilyReviewExportPackage",
    "WebFontBuilder",
    # Performance
    "PerformanceBenchmark",
    "PerformanceReport",
    "PerformanceResult",
    "PerformanceMeasurement",
    "PerformanceBaselineReport",
    "PerformanceRegressionPackage",
    # Loader
    "FontLoader",
    "FontSourceInfo",
    "LoadedFont",
    "extract_font_metadata",
    "FontCleaner",
    "WebFontOptimizerDecision",
    "WebFontOptimizerPackageWithDecision",
    "analyze_font_for_web_optimization",
    "build_web_optimizer_package",
    "build_web_optimizer_package_with_plan",
    # Visual proofing
    "run_visual_proof",
    # Capability discovery
    "FontCapabilityBuilder",
    "FontCapabilityReport",
    "AxisDescription",
    "ScriptCoverage",
    "CSSHints",
    "ReleaseRisk",
    "CapabilitySummary",
    # Format classes
    "TtfFont",
    "CffFont",
    "Cff2Font",
    "Type1Font",
    "WoffFont",
    "Woff2Font",
    "EotFont",
]
