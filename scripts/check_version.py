#!/usr/bin/env python3
"""Validate that HassCheck version declarations cannot drift.

The project version in pyproject.toml is the source of truth. Runtime metadata,
CLI output, and optional release tags must match it exactly.
"""

from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path
from typing import Final

from typer.testing import CliRunner

ROOT: Final = Path(__file__).resolve().parents[1]
VERSION_PATTERN: Final = re.compile(r"\d+\.\d+\.\d+")


def read_pyproject_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as file:
        pyproject = tomllib.load(file)

    version = pyproject["project"]["version"]
    if not isinstance(version, str):
        raise TypeError("project.version in pyproject.toml must be a string")
    return version


def validate_semver(version: str, source: str) -> None:
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError(f"{source} must use X.Y.Z format, got {version!r}")


def read_runtime_versions() -> dict[str, str]:
    sys.path.insert(0, str(ROOT / "src"))

    from hasscheck import __version__  # noqa: PLC0415
    from hasscheck.cli import app  # noqa: PLC0415
    from hasscheck.models import ToolInfo  # noqa: PLC0415

    result = CliRunner().invoke(app, ["--version"])
    if result.exit_code != 0:
        raise RuntimeError(f"hasscheck --version failed: {result.output}")

    return {
        "src/hasscheck/__init__.py __version__": __version__,
        "ToolInfo.version": ToolInfo().version,
        "hasscheck --version": result.output.strip().removeprefix("hasscheck "),
    }


def tag_to_version(tag: str) -> str:
    if not tag.startswith("v"):
        raise ValueError(f"release tag must start with 'v', got {tag!r}")
    version = tag[1:]
    validate_semver(version, "release tag")
    return version


def check_versions(tag: str | None = None) -> list[str]:
    errors: list[str] = []

    pyproject_version = read_pyproject_version()

    versions = {"pyproject.toml project.version": pyproject_version}
    versions.update(read_runtime_versions())

    for source, version in versions.items():
        try:
            validate_semver(version, source)
        except ValueError as exc:
            errors.append(str(exc))

        if version != pyproject_version:
            errors.append(
                f"{source} is {version!r}, expected {pyproject_version!r} "
                "from pyproject.toml"
            )

    if tag is not None:
        try:
            tag_version = tag_to_version(tag)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if tag_version != pyproject_version:
                errors.append(
                    f"release tag {tag!r} points to version {tag_version!r}, "
                    f"expected 'v{pyproject_version}'"
                )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check that package, runtime, CLI, and optional tag versions match."
    )
    parser.add_argument(
        "--tag",
        help="Optional release tag to validate, for example v0.3.0.",
    )
    args = parser.parse_args(argv)

    try:
        errors = check_versions(tag=args.tag)
    except Exception as exc:  # pragma: no cover - defensive CLI guard
        print(f"version check failed: {exc}", file=sys.stderr)
        return 1

    if errors:
        for error in errors:
            print(f"version mismatch: {error}", file=sys.stderr)
        return 1

    print("version check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
