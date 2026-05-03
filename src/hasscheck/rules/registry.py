from __future__ import annotations

from hasscheck.rules.base import RuleDefinition
from hasscheck.rules.brand import RULES as BRAND_RULES
from hasscheck.rules.ci import RULES as CI_RULES
from hasscheck.rules.config_flow import RULES as CONFIG_FLOW_RULES
from hasscheck.rules.deprecations import RULES as DEPRECATIONS_RULES
from hasscheck.rules.diagnostics import RULES as DIAGNOSTICS_RULES
from hasscheck.rules.docs import RULES as DOCS_RULES
from hasscheck.rules.docs_readme import RULES as DOCS_README_RULES
from hasscheck.rules.entity import RULES as ENTITY_RULES
from hasscheck.rules.hacs_structure import RULES as HACS_STRUCTURE_RULES
from hasscheck.rules.init_module import RULES as INIT_MODULE_RULES
from hasscheck.rules.maintenance import RULES as MAINTENANCE_RULES
from hasscheck.rules.manifest import RULES as MANIFEST_RULES
from hasscheck.rules.repairs import RULES as REPAIRS_RULES
from hasscheck.rules.repository import RULES as REPOSITORY_RULES
from hasscheck.rules.tests import RULES as TESTS_RULES
from hasscheck.rules.version_identity import RULES as VERSION_IDENTITY_RULES

RULES = [
    *HACS_STRUCTURE_RULES,
    *BRAND_RULES,
    *MANIFEST_RULES,
    *CONFIG_FLOW_RULES,
    *DIAGNOSTICS_RULES,
    *REPAIRS_RULES,
    *DOCS_RULES,
    *DOCS_README_RULES,
    *REPOSITORY_RULES,
    *TESTS_RULES,
    *CI_RULES,
    *INIT_MODULE_RULES,
    *ENTITY_RULES,
    *MAINTENANCE_RULES,
    *VERSION_IDENTITY_RULES,
    *DEPRECATIONS_RULES,
]
RULES_BY_ID: dict[str, RuleDefinition] = {}
for _rule in RULES:
    if _rule.id in RULES_BY_ID:
        raise RuntimeError(
            f"Duplicate rule ID '{_rule.id}' — "
            f"each rule must have a unique ID across all modules."
        )
    RULES_BY_ID[_rule.id] = _rule
