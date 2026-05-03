import pytest
import yaml

from hasscheck.config import HassCheckConfig
from hasscheck.init import init_project


def test_init_creates_hasscheck_yaml_and_workflow(tmp_path):
    artifacts = init_project(tmp_path)

    yaml_target = tmp_path / "hasscheck.yaml"
    workflow_target = tmp_path / ".github" / "workflows" / "hasscheck.yml"

    assert yaml_target.is_file()
    assert workflow_target.is_file()
    assert {a.target for a in artifacts} == {yaml_target, workflow_target}
    assert all(a.created for a in artifacts)


def test_init_yaml_is_valid_hasscheck_config(tmp_path):
    init_project(tmp_path)
    parsed = yaml.safe_load((tmp_path / "hasscheck.yaml").read_text())
    config = HassCheckConfig(**parsed)
    assert config.schema_version == "0.7.0"
    assert config.rules == {}
    assert config.gate is None


def test_init_dry_run_does_not_write(tmp_path, capsys):
    artifacts = init_project(tmp_path, dry_run=True)
    assert not (tmp_path / "hasscheck.yaml").exists()
    assert not (tmp_path / ".github" / "workflows" / "hasscheck.yml").exists()
    assert all(a.created is False for a in artifacts)
    out = capsys.readouterr().out
    assert "schema_version" in out
    assert "uses: actions/checkout" in out


def test_init_refuses_to_overwrite_existing_yaml(tmp_path):
    (tmp_path / "hasscheck.yaml").write_text("# pre-existing\n")
    with pytest.raises(FileExistsError):
        init_project(tmp_path)
    assert (tmp_path / "hasscheck.yaml").read_text() == "# pre-existing\n"


def test_init_refuses_to_overwrite_existing_workflow(tmp_path):
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("# pre-existing\n")
    with pytest.raises(FileExistsError):
        init_project(tmp_path)


def test_init_force_overwrites_existing_files(tmp_path):
    (tmp_path / "hasscheck.yaml").write_text("# old yaml\n")
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("# old workflow\n")

    init_project(tmp_path, force=True)

    yaml_text = (tmp_path / "hasscheck.yaml").read_text()
    workflow_text = workflow.read_text()
    assert "# old yaml" not in yaml_text
    assert "# old workflow" not in workflow_text
    assert "schema_version" in yaml_text
    assert "uses: actions/checkout" in workflow_text


def test_init_skip_action_only_writes_yaml(tmp_path):
    artifacts = init_project(tmp_path, skip_action=True)
    assert (tmp_path / "hasscheck.yaml").is_file()
    assert not (tmp_path / ".github").exists()
    assert len(artifacts) == 1
    assert artifacts[0].target == tmp_path / "hasscheck.yaml"


def test_init_invalid_path_raises_value_error(tmp_path):
    missing = tmp_path / "nope"
    with pytest.raises(ValueError):
        init_project(missing)


# ---------- --enable-publish flag (v0.8) ----------


def test_init_enable_publish_false_writes_standard_workflow(tmp_path):
    """Default (enable_publish=False) → workflow without emit-publish."""
    init_project(tmp_path, enable_publish=False)
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    content = workflow.read_text()
    assert "emit-publish" not in content


def test_init_enable_publish_true_writes_publish_workflow(tmp_path):
    """enable_publish=True → workflow with id-token: write and emit-publish: 'true'."""
    init_project(tmp_path, enable_publish=True)
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    content = workflow.read_text()
    assert "id-token: write" in content
    assert "emit-publish: 'true'" in content


def test_init_enable_publish_force_overwrites_existing_workflow(tmp_path):
    """--force --enable-publish over existing standard workflow → swap to publish variant."""
    init_project(tmp_path)
    workflow = tmp_path / ".github" / "workflows" / "hasscheck.yml"
    original_content = workflow.read_text()
    assert "emit-publish" not in original_content

    init_project(tmp_path, force=True, enable_publish=True)
    new_content = workflow.read_text()
    assert "emit-publish: 'true'" in new_content
    assert "id-token: write" in new_content


def test_init_enable_publish_missing_template_raises(tmp_path, monkeypatch):
    """Missing template file raises FileNotFoundError before writing anything."""
    import hasscheck.init as init_module

    original_load = init_module.load_template

    def patched_load(name: str) -> str:
        if name == "github_action_publish.yml.tmpl":
            raise FileNotFoundError(f"Template not found: {name}")
        return original_load(name)

    monkeypatch.setattr(init_module, "load_template", patched_load)

    with pytest.raises(FileNotFoundError):
        init_project(tmp_path, enable_publish=True)


# ---------- Phase 7: scaffold schema_version bump to 0.7.0 (#146) ----------


def test_init_yaml_contains_schema_version_070(tmp_path):
    """Scaffold output must contain schema_version: '0.7.0' (bumped from 0.6.0 in #146)."""
    init_project(tmp_path, skip_action=True)
    content = (tmp_path / "hasscheck.yaml").read_text()
    assert '"0.7.0"' in content or "'0.7.0'" in content, (
        f"Expected schema_version '0.7.0' in scaffold output, got:\n{content}"
    )
