from __future__ import annotations

from hasscheck.rules.hacs_structure import RULES as HACS_STRUCTURE_RULES
from hasscheck.rules.manifest import RULES as MANIFEST_RULES

RULES = [*HACS_STRUCTURE_RULES, *MANIFEST_RULES]
RULES_BY_ID = {rule.id: rule for rule in RULES}
