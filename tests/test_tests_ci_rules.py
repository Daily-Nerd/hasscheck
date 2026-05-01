from hasscheck.checker import run_check
from hasscheck.models import RuleStatus


def findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


def test_tests_folder_passes_when_tests_directory_exists(tmp_path) -> None:
    (tmp_path / "tests").mkdir()

    finding = findings_for(tmp_path)["tests.folder.exists"]

    assert finding.status is RuleStatus.PASS


def test_tests_folder_warns_when_missing(tmp_path) -> None:
    finding = findings_for(tmp_path)["tests.folder.exists"]

    assert finding.status is RuleStatus.WARN
    assert finding.fix is not None


def test_github_actions_passes_with_yml_or_yaml_workflow(tmp_path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "tests.yml").write_text("name: tests\n", encoding="utf-8")

    finding = findings_for(tmp_path)["ci.github_actions.exists"]

    assert finding.status is RuleStatus.PASS
    assert finding.path == ".github/workflows/tests.yml"


def test_github_actions_accepts_yaml_extension(tmp_path) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yaml").write_text("name: ci\n", encoding="utf-8")

    finding = findings_for(tmp_path)["ci.github_actions.exists"]

    assert finding.status is RuleStatus.PASS
    assert finding.path == ".github/workflows/ci.yaml"


def test_github_actions_warns_when_missing(tmp_path) -> None:
    finding = findings_for(tmp_path)["ci.github_actions.exists"]

    assert finding.status is RuleStatus.WARN
    assert finding.fix is not None


def test_tests_ci_category_is_used(tmp_path) -> None:
    (tmp_path / "tests").mkdir()
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "tests.yml").write_text("name: tests\n", encoding="utf-8")

    findings = findings_for(tmp_path)

    assert findings["tests.folder.exists"].category == "tests_ci"
    assert findings["ci.github_actions.exists"].category == "tests_ci"
