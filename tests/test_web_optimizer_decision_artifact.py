import pathlib

from aspose_font.preview import PreviewImage
from aspose_font.web import WebFontOptimizer


def test_decision_artifact_generated_and_written(tmp_path: pathlib.Path, roboto):
    """Verify that enabling decision_artifact produces a PreviewImage and writes it to disk."""
    # Build optimizer package with decision artifact enabled
    package = WebFontOptimizer.build(
        roboto,
        decision_artifact=True,
        decision_report=False,  # decision report not needed for this test
    )
    # Ensure the artifact is present and of correct type
    assert isinstance(package.decision_artifact, PreviewImage)
    # Write the package to a temporary directory
    written_paths = package.write_to(tmp_path)
    # Locate the artifact file path in the written list
    artifact_path = None
    for p in written_paths:
        if p.name == package.decision_artifact.filename:
            artifact_path = p
            break
    assert artifact_path is not None, "Decision artifact file was not written"
    # Verify file exists and starts with PNG signature
    assert artifact_path.is_file()
    data = artifact_path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), "Artifact does not contain valid PNG data"
