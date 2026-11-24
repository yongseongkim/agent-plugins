"""Install the video-analysis Agent Skill for a user or a project."""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path


PACKAGE = Path(__file__).resolve().parent / "skills" / "video-analysis"
USER_DIRS = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "antigravity": ".gemini/config/skills",
}
PROJECT_DIRS = {**USER_DIRS, "antigravity": ".agents/skills"}


def contents(folder):
    return {
        p.relative_to(folder): p.read_bytes() for p in folder.rglob("*")
        if p.is_file() and "__pycache__" not in p.relative_to(folder).parts and p.suffix != ".pyc"
    }


def install(root, directories, agents):
    package_files = contents(PACKAGE)
    if Path("SKILL.md") not in package_files:
        raise ValueError(f"Missing skill package at {PACKAGE}")
    # Several clients can share a directory, including through a project symlink.
    targets = list(dict.fromkeys((root / directories[a]).resolve() / PACKAGE.name for a in agents))
    missing = []
    for target in targets:
        if target.is_dir() and contents(target) == package_files:
            print(f"Already installed: {target}")
        elif target.exists() or target.is_symlink():
            raise ValueError(f"Different installation at {target}. Compare it with {PACKAGE} before replacing it.")
        else:
            missing.append(target)

    for target in missing:
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
            staged = Path(tmp) / PACKAGE.name
            shutil.copytree(PACKAGE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            staged.rename(target)
        print(f"Installed: {target}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--user", action="store_true", help="Install in the user's skill directories")
    scope.add_argument("--project", type=Path, metavar="DIR", help="Install in an existing project directory")
    parser.add_argument("--agent", choices=USER_DIRS, action="append",
                        help="Select a client (repeatable). Default: all three")
    args = parser.parse_args()
    root = Path.home() if args.user else args.project.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Directory does not exist: {root}")
    try:
        install(root, USER_DIRS if args.user else PROJECT_DIRS, args.agent or USER_DIRS.keys())
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
