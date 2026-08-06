from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RULES: dict[str, tuple[str, ...]] = {
    "L0": (
        r"^PROJECT_MASTER_PROMPT\.md$", r"^README\.md$", r"^contracts/", r"^infra/", r"^scripts/",
        r"^\.github/", r"^\.(?:env\.example|nvmrc|python-version|editorconfig|gitattributes|gitignore|dockerignore)$",
        r"^demo/(?:package(?:-lock)?\.json|eslint\.config\.js|vitest\.config\.ts|vite\.config\.ts|tsconfig\.json|tailwind\.config\.js|postcss\.config\.js)$",
        r"^demo/test/", r"^demo/src/api/generated/",
        r"^backend/(?:pyproject\.toml|uv\.lock|alembic\.ini|README\.md)$", r"^backend/migrations/",
        r"^backend/app/(?:main\.py|models_registry\.py)$", r"^backend/app/api/", r"^backend/app/contracts/",
        r"^backend/app/(?:__init__\.py|domains/__init__\.py)$", r"^backend/tests/test_app_bootstrap\.py$",
    ),
    "M1": (r"^demo/src/pages/(?:Dashboard|BidCreate|TaskDetail)\.tsx$", r"^demo/src/features/bids/"),
    "M2": (
        r"^demo/src/pages/(?:EvaluationDashboard|EvaluationCreate|EvaluationTaskDetail|SupplierPortal)\.tsx$",
        r"^demo/src/features/(?:evaluations|portal)/",
    ),
    "M3": (
        r"^demo/src/(?:App|main)\.tsx$", r"^demo/src/index\.css$", r"^demo/src/layouts/", r"^demo/src/components/common/",
        r"^demo/src/api/(?!generated/)", r"^demo/src/features/(?:admin|libraries)/",
        r"^demo/src/pages/(?:Login|QualificationLibrary|FragmentLibrary|UserPermissions|SystemSettings)\.tsx$",
        r"^demo/src/context/", r"^demo/src/mock/",
    ),
    "M4": (
        r"^backend/app/core/", r"^backend/app/domains/(?:auth|users|files|jobs|notifications|settings|audit|search|health)/",
        r"^backend/tests/(?:platform|auth|users|files|jobs|notifications|settings|audit|search|health)/",
    ),
    "M5": (
        r"^backend/app/domains/(?:bids|qualifications|fragments|documents)/",
        r"^backend/tests/(?:bids|qualifications|fragments|documents)/",
    ),
    "M6": (
        r"^backend/app/domains/(?:evaluations|portal|pricing|scoring)/",
        r"^backend/tests/(?:evaluations|portal|pricing|scoring)/",
    ),
    "M7": (r"^backend/app/(?:ai|workers)/", r"^backend/tests/ai/", r"^e2e/"),
}


def member_from_branch(branch: str) -> str:
    if branch.startswith(("docs/l0-", "chore/l0-", "contract/")):
        return "L0"
    match = re.match(r"^(?:feat|fix)/(m[1-7])-", branch, re.IGNORECASE)
    if not match:
        raise ValueError(f"branch name does not identify an owner: {branch}")
    return match.group(1).upper()


def changed_files(base: str) -> list[str]:
    command = ["git", "diff", "--name-only", f"{base}...HEAD"]
    output = subprocess.check_output(command, cwd=ROOT, text=True, encoding="utf-8")
    return [line.strip().replace("\\", "/") for line in output.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PR paths against PROJECT_MASTER_PROMPT ownership")
    parser.add_argument("--branch", required=True)
    parser.add_argument("--base", default="origin/develop")
    args = parser.parse_args()

    member = member_from_branch(args.branch)
    patterns = [re.compile(pattern) for pattern in RULES[member]]
    files = changed_files(args.base)
    violations = [path for path in files if not any(pattern.search(path) for pattern in patterns)]
    if violations:
        print(f"[FAIL] {member} branch modifies files outside its ownership:", file=sys.stderr)
        for path in violations:
            print(f"  - {path}", file=sys.stderr)
        return 1
    print(f"[OK] {member} owns all {len(files)} changed files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
