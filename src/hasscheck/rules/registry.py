from __future__ import annotations

from hasscheck.rules.brand import RULES as BRAND_RULES
from hasscheck.rules.config_flow import RULES as CONFIG_FLOW_RULES
from hasscheck.rules.diagnostics import RULES as DIAGNOSTICS_RULES
from hasscheck.rules.docs import RULES as DOCS_RULES
from hasscheck.rules.hacs_structure import RULES as HACS_STRUCTURE_RULES
from hasscheck.rules.manifest import RULES as MANIFEST_RULES
from hasscheck.rules.repairs import RULES as REPAIRS_RULES
from hasscheck.rules.repository import RULES as REPOSITORY_RULES

RULES = [*HACS_STRUCTURE_RULES, *BRAND_RULES, *MANIFEST_RULES, *CONFIG_FLOW_RULES, *DIAGNOSTICS_RULES, *REPAIRS_RULES, *DOCS_RULES, *REPOSITORY_RULES]
RULES_BY_ID = {rule.id: rule for rule in RULES}
