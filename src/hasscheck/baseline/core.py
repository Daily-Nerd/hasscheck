"""Baseline data layer: models, hashing, partition, YAML I/O.

Pure, no Typer, no Rich. Imported by both the CLI subapp and `cli.check`.
The hash policy is documented in ADR 0016 — message normalization is the
only field-stability lever; rule_id and path must match exactly.
"""
