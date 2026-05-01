from pathlib import Path

import yaml


def test_emit_badges_input_exists():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    assert "emit-badges" in cfg["inputs"]


def test_emit_badges_default_is_false():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    assert cfg["inputs"]["emit-badges"]["default"] == "false"


def test_badges_out_dir_input_exists():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    assert "badges-out-dir" in cfg["inputs"]


def test_badges_out_dir_default_is_badges():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    assert cfg["inputs"]["badges-out-dir"]["default"] == "badges"


def test_generate_badges_step_is_conditional():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    steps = cfg["runs"]["steps"]
    badge_step = next((s for s in steps if s.get("name") == "Generate badges"), None)
    assert badge_step is not None
    assert "emit-badges" in badge_step.get("if", "")


def test_upload_badges_artifact_step_exists():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    steps = cfg["runs"]["steps"]
    upload_step = next(
        (s for s in steps if s.get("name") == "Upload badges artifact"), None
    )
    assert upload_step is not None
    assert upload_step["with"]["name"] == "hasscheck-badges"
