from __future__ import annotations


class BadgePolicyError(Exception):
    pass


FORBIDDEN_LABEL_TOKENS: frozenset[str] = frozenset(
    {"certified", "safe", "approved", "hacs ready", "community ready"}
)

ALLOWED_SUFFIXES: frozenset[str] = frozenset(
    {"Passing", "Partial", "Issues", "Present", "Signals Available"}
)

# Maps category_id → left-hand badge label (human readable)
# Must match CATEGORY_LABELS in checker.py exactly
CATEGORY_LABELS: dict[str, str] = {
    "hacs_structure": "HACS Structure",
    "manifest_metadata": "Manifest",
    "modern_ha_patterns": "Config Flow",
    "diagnostics_repairs": "Diagnostics",
    "docs_support": "Docs",
    "maintenance_signals": "Maintenance",
    "tests_ci": "Tests & CI",
}

# These categories use "Present"/"Missing" instead of "Passing"/"Issues"
PRESENT_ABSENT_CATEGORIES: frozenset[str] = frozenset(
    {
        "diagnostics_repairs",
        "modern_ha_patterns",
    }
)

# Bump only when badge manifest JSON structure changes.
BADGE_MANIFEST_SCHEMA_VERSION: str = "0.6.0"


def assert_label_is_clean(label: str) -> None:
    lower = label.lower()
    for token in FORBIDDEN_LABEL_TOKENS:
        if token in lower:
            raise BadgePolicyError(
                f"Badge label {label!r} contains forbidden token {token!r}. "
                f"See idea.md §12 for allowed language."
            )
