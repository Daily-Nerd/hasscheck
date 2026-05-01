"""End-to-end tests for generate_badges()."""

from __future__ import annotations

import json
from pathlib import Path

from hasscheck.badges.generator import generate_badges
from hasscheck.models import (
    CategorySignal,
    HassCheckReport,
    ProjectInfo,
    ReportSummary,
)


def _make_report(*categories: CategorySignal) -> HassCheckReport:
    return HassCheckReport(
        project=ProjectInfo(path="/tmp/test"),
        summary=ReportSummary(categories=list(categories)),
        findings=[],
    )


def test_generate_badges_writes_manifest(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=10,
            points_possible=10,
        ),
    )
    generate_badges(report, out_dir=tmp_path)
    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.6.0"
    assert isinstance(data["artifacts"], list)


def test_generate_badges_na_category_omitted(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=5,
            points_possible=10,
        ),
        CategorySignal(
            id="manifest_metadata",
            label="Manifest",
            points_awarded=0,
            points_possible=0,
        ),  # fully N/A — should be omitted
    )
    artifacts = generate_badges(report, out_dir=tmp_path)
    artifact_ids = [a.category_id for a in artifacts]
    assert "hacs_structure" in artifact_ids
    assert "manifest_metadata" not in artifact_ids
    assert not (tmp_path / "manifest_metadata.json").exists()


def test_generate_badges_correct_file_count(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=10,
            points_possible=10,
        ),
        CategorySignal(
            id="tests_ci", label="Tests & CI", points_awarded=3, points_possible=5
        ),
    )
    artifacts = generate_badges(report, out_dir=tmp_path)
    # 2 categories + 1 umbrella = 3 artifacts
    assert len(artifacts) == 3
    assert (tmp_path / "hacs_structure.json").exists()
    assert (tmp_path / "tests_ci.json").exists()
    assert (tmp_path / "hasscheck.json").exists()


def test_generate_badges_emit_umbrella_false(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=10,
            points_possible=10,
        ),
    )
    artifacts = generate_badges(report, out_dir=tmp_path, emit_umbrella=False)
    artifact_ids = [a.category_id for a in artifacts]
    assert "umbrella" not in artifact_ids
    assert not (tmp_path / "hasscheck.json").exists()


def test_generate_badges_include_filter(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=10,
            points_possible=10,
        ),
        CategorySignal(
            id="tests_ci", label="Tests & CI", points_awarded=3, points_possible=5
        ),
    )
    artifacts = generate_badges(
        report, out_dir=tmp_path, include={"hacs_structure"}, emit_umbrella=False
    )
    artifact_ids = [a.category_id for a in artifacts]
    assert artifact_ids == ["hacs_structure"]
    assert (tmp_path / "hacs_structure.json").exists()
    assert not (tmp_path / "tests_ci.json").exists()


def test_generate_badges_manifest_schema_version(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=5,
            points_possible=10,
        ),
    )
    generate_badges(report, out_dir=tmp_path)
    data = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.6.0"


def test_generate_badges_endpoint_json_valid(tmp_path: Path) -> None:
    report = _make_report(
        CategorySignal(
            id="hacs_structure",
            label="HACS Structure",
            points_awarded=10,
            points_possible=10,
        ),
    )
    generate_badges(report, out_dir=tmp_path, emit_umbrella=False)
    endpoint = json.loads(
        (tmp_path / "hacs_structure.json").read_text(encoding="utf-8")
    )
    assert endpoint["schemaVersion"] == 1
    assert endpoint["label"] == "HACS Structure"
    assert endpoint["message"] == "Passing"
    assert endpoint["color"] == "brightgreen"
    assert endpoint["cacheSeconds"] == 300
