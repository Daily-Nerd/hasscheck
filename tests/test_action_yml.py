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


def test_emit_publish_input_exists_and_defaults_false():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    assert "emit-publish" in cfg["inputs"]
    assert cfg["inputs"]["emit-publish"]["default"] == "false"


def test_publish_endpoint_input_defaults_to_hasscheck_io():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    assert "publish-endpoint" in cfg["inputs"]
    assert cfg["inputs"]["publish-endpoint"]["default"] == "https://hasscheck.io"


def test_oidc_step_is_conditional_on_emit_publish():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    steps = cfg["runs"]["steps"]
    oidc_step = next(
        (s for s in steps if s.get("name") == "Request GitHub OIDC token"), None
    )
    assert oidc_step is not None
    assert "emit-publish" in oidc_step.get("if", "")


def test_publish_step_is_conditional_on_emit_publish():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    steps = cfg["runs"]["steps"]
    publish_step = next((s for s in steps if s.get("name") == "Publish report"), None)
    assert publish_step is not None
    assert "emit-publish" in publish_step.get("if", "")
    assert publish_step["env"]["HASSCHECK_OIDC_TOKEN"].startswith("${{ steps.oidc")


def test_publish_step_calls_hasscheck_publish_with_endpoint():
    cfg = yaml.safe_load(Path("action.yml").read_text())
    steps = cfg["runs"]["steps"]
    publish_step = next((s for s in steps if s.get("name") == "Publish report"), None)
    assert publish_step is not None
    run_block = publish_step["run"]
    assert "hasscheck publish" in run_block
    assert "--to" in run_block
    assert "publish-endpoint" in run_block
