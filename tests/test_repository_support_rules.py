from hasscheck.checker import run_check
from hasscheck.models import RuleStatus


def write_integration(root) -> None:
    integration = root / "custom_components" / "demo"
    integration.mkdir(parents=True)
    (integration / "manifest.json").write_text('{"domain":"demo"}', encoding="utf-8")


def findings_for(root):
    return {finding.rule_id: finding for finding in run_check(root).findings}


def test_readme_and_license_pass_when_present(tmp_path) -> None:
    write_integration(tmp_path)
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")

    findings = findings_for(tmp_path)

    assert findings["docs.readme.exists"].status is RuleStatus.PASS
    assert findings["repo.license.exists"].status is RuleStatus.PASS


def test_readme_and_license_warn_when_missing(tmp_path) -> None:
    write_integration(tmp_path)

    findings = findings_for(tmp_path)

    assert findings["docs.readme.exists"].status is RuleStatus.WARN
    assert findings["docs.readme.exists"].fix is not None
    assert findings["repo.license.exists"].status is RuleStatus.WARN
    assert findings["repo.license.exists"].fix is not None


def test_brand_icon_passes_when_present(tmp_path) -> None:
    write_integration(tmp_path)
    brand = tmp_path / "custom_components" / "demo" / "brand"
    brand.mkdir()
    (brand / "icon.png").write_bytes(b"fake-png-for-presence-check")

    finding = findings_for(tmp_path)["brand.icon.exists"]

    assert finding.status is RuleStatus.PASS
    assert finding.source.url == "https://www.hacs.xyz/docs/publish/integration/"


def test_brand_icon_warns_when_missing_for_detected_integration(tmp_path) -> None:
    write_integration(tmp_path)

    finding = findings_for(tmp_path)["brand.icon.exists"]

    assert finding.status is RuleStatus.WARN
    assert finding.fix is not None


def test_brand_icon_not_applicable_without_integration(tmp_path) -> None:
    finding = findings_for(tmp_path)["brand.icon.exists"]

    assert finding.status is RuleStatus.NOT_APPLICABLE
