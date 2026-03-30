#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import tomllib  # Python 3.11+
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
NIX_FILE = ROOT / "nix" / "drawiterm.nix"

_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")


def parse_version(s: str) -> tuple[int, int, int, str | None, int | None]:
    m = _VERSION_RE.fullmatch(s)
    if not m:
        raise ValueError(f"Unsupported version format: {s!r}")
    major, minor, patch = map(int, m.group(1, 2, 3))
    pre_tag = m.group(4)
    pre_num = int(m.group(5)) if m.group(5) else None
    return major, minor, patch, pre_tag, pre_num


def format_version(
    major: int, minor: int, patch: int, pre_tag: str | None, pre_num: int | None
) -> str:
    if pre_tag:
        if pre_num is None:
            pre_num = 1
        return f"{major}.{minor}.{patch}{pre_tag}{pre_num}"
    return f"{major}.{minor}.{patch}"


def bump_version(
    cur: str,
    part: str,  # "major" | "minor" | "patch"
    pre: str | None,  # "a" | "b" | "rc" | None
    finalize: bool,
) -> str:
    major, minor, patch, pre_tag, pre_num = parse_version(cur)

    if finalize and pre_tag:
        # Drop prerelease, keep base version
        return format_version(major, minor, patch, None, None)

    if part == "major":
        major += 1
        minor = 0
        patch = 0
        pre_tag = pre
        pre_num = 1 if pre else None
    elif part == "minor":
        minor += 1
        patch = 0
        pre_tag = pre
        pre_num = 1 if pre else None
    else:  # patch
        if pre:
            if pre_tag == pre:
                pre_num = (pre_num or 0) + 1
            else:
                pre_tag = pre
                pre_num = 1
        else:
            patch += 1
            pre_tag = None
            pre_num = None

    return format_version(major, minor, patch, pre_tag, pre_num)


def read_pyproject_version() -> str:
    with PYPROJECT.open("rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


def update_pyproject_version(new_version: str) -> None:
    lines = PYPROJECT.read_text(encoding="utf-8").splitlines(keepends=True)
    out: list[str] = []
    in_project = False
    replaced = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_project = stripped == "[project]"
        if in_project and stripped.startswith("version"):
            line = re.sub(
                r'^(?P<indent>\s*version\s*=\s*)"(.*?)"(?P<trail>\s*)$',
                rf'\g<indent>"{new_version}"\g<trail>',
                line,
            )
            replaced = True
            in_project = False  # only once
        out.append(line)
    if not replaced:
        raise RuntimeError("Failed to update version in pyproject.toml")
    PYPROJECT.write_text("".join(out), encoding="utf-8")


def update_nix_version(new_version: str) -> None:
    if not NIX_FILE.exists():
        return
    text = NIX_FILE.read_text(encoding="utf-8")
    new_text, n = re.subn(
        r'(?m)^(\s*version\s*=\s*")([^"]*)(";\s*)$',
        lambda m: f"{m.group(1)}{new_version}{m.group(3)}",
        text,
        count=1,
    )
    if n == 0:
        raise RuntimeError("Failed to update version in nix/drawiterm.nix")
    NIX_FILE.write_text(new_text, encoding="utf-8")


def run(*args: str) -> None:
    subprocess.run(list(args), check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Bump version, commit, tag.")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--major", action="store_true", help="Bump major version")
    grp.add_argument("--minor", action="store_true", help="Bump minor version")
    grp.add_argument("--patch", action="store_true", help="Bump patch version (default)")
    ap.add_argument(
        "--pre",
        choices=("a", "b", "rc"),
        help=(
            "Start or increment a pre-release (a/b/rc). "
            "For patch: increments same kind if present."
        ),
    )
    ap.add_argument("--finalize", action="store_true", help="Drop any pre-release (no other bump).")
    ap.add_argument("--no-commit", action="store_true", help="Do not create a commit.")
    ap.add_argument("--no-tag", action="store_true", help="Do not create a git tag.")
    ap.add_argument("--push", action="store_true", help="Push current branch and tags.")
    args = ap.parse_args()

    if args.finalize and args.pre:
        ap.error("Cannot use --pre with --finalize.")

    part = "patch"
    if args.major:
        part = "major"
    elif args.minor:
        part = "minor"
    elif args.patch:
        part = "patch"

    cur = read_pyproject_version()
    new = bump_version(cur, part=part, pre=args.pre, finalize=args.finalize)

    update_pyproject_version(new)
    update_nix_version(new)

    print(f"Bumped version: {cur} -> {new}")

    if not args.no_commit:
        run("git", "add", str(PYPROJECT))
        if NIX_FILE.exists():
            run("git", "add", str(NIX_FILE))
        run("git", "commit", "-m", f"release: bump version to {new}")

    if not args.no_tag:
        run("git", "tag", "-a", f"v{new}", "-m", f"v{new}")

    if args.push:
        run("git", "push", "origin", "HEAD")
        if not args.no_tag:
            run("git", "push", "origin", f"v{new}")

    print("Done.")
    print("Next steps:")
    print("  - Verify CHANGELOG/README if applicable.")
    print("  - Push (if not using --push): git push origin HEAD && git push origin --tags")
    print(f"  - GitHub Actions Release workflow will run for tag v{new}.")


if __name__ == "__main__":
    main()
