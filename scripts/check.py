#!/usr/bin/env python3
"""ハーネス本体（HARNESS_ROOT）に対して CI（harness-ci.yml）と同等の検査を一括実行する。

使い方（この保守プロジェクトのルートで）:
    .venv\\Scripts\\python scripts\\check.py            # 全検査（ubuntu ジョブ相当 + windows ジョブ相当）
    .venv\\Scripts\\python scripts\\check.py --quick    # 構造検証・生成物差分・フック selftest だけ
    .venv\\Scripts\\python scripts\\check.py --list     # 実行する検査の一覧を表示して終了
    .venv\\Scripts\\python scripts\\check.py --only validate,selftest-sh   # 名前で絞る

検査項目の正は常にハーネス側の `.github/workflows/harness-ci.yml`。この一覧と食い違ったら
CI 側に合わせて本スクリプトを直す（CONTRIBUTING.md の方針と同じ）。
Claude Code CLI を使う CI ステップ（plugin validate / --init-only / host-canary 実走）は
開発機では任意のため既定で省く（--with-claude で含める）。
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
HARNESS_ROOT = Path(os.environ.get("HARNESS_ROOT", "D:/vscode-worspace/CreateAppl")).resolve()
# 1 項目の上限秒。超えたら FAIL にして次へ進む（stdin 待ちなどで止まったフックを放置しない）
DEFAULT_TIMEOUT = 300
TIMEOUTS = {"selftest-ps1": 900, "selftest-sh": 600}
PY = sys.executable  # .venv の Python 3.11（CI と同じ版）を想定

# (name, argv, quick?, needs_claude?)  argv の "python" は実行中の Python に置換する
STEPS: list[tuple[str, list[str], bool, bool]] = [
    # ---- ubuntu ジョブ相当 ----
    ("validate",            ["python", "tools/validate-harness.py", "--ledger-strict"], True, False),
    ("gen-docs-check",      ["python", "tools/gen-docs.py", "--check"], True, False),
    ("gen-docs-selftest",   ["python", "tools/gen-docs.py", "--selftest"], False, False),
    ("freshness-lint",      ["python", "tools/freshness-lint.py"], False, False),
    ("freshness-selftest",  ["python", "tools/freshness-lint.py", "--selftest"], False, False),
    ("release-tag-selftest", ["python", "tools/release-tag.py", "--selftest"], False, False),
    ("host-canary-selftest", ["python", "tools/host-canary.py", "--selftest"], False, False),
    ("release-tag-check",   ["python", "tools/release-tag.py", "--check"], False, False),
    ("effort-kpi",          ["python", "tools/effort-report.py", "--kpi"], False, False),
    ("adapters-check",      ["python", "tools/generate-adapters.py", "--check"], True, False),
    ("model-policy",        ["python", "tools/model_policy.py", "--selftest"], False, False),
    ("copilot-entry-skills", ["python", "tools/copilot_entry_skills.py", "--selftest"], False, False),
    ("plugin-manifests",    ["python", "tools/plugin_manifests.py", "--selftest"], False, False),
    ("claude-plugin-validate", ["claude", "plugin", "validate", "."], False, True),
    ("host-canary",         ["python", "tools/host-canary.py"], False, True),
    ("selftest-sh",         ["bash", ".github/hooks/scripts/selftest.sh"], True, False),
    ("log-effort",          ["python", ".github/hooks/scripts/log-effort.py", "--selftest"], False, False),
    ("session-receipt",     ["python", "tools/session-receipt.py", "--selftest"], False, False),
    ("statusline",          ["python", ".github/hooks/scripts/statusline.py", "--selftest"], False, False),
    ("log-subagent",        ["python", ".github/hooks/scripts/log-subagent.py", "--selftest"], False, False),
    ("session-baseline",    ["python", ".github/hooks/scripts/session-baseline.py", "--selftest"], False, False),
    ("effort-report",       ["python", "tools/effort-report.py", "--selftest"], False, False),
    ("remind-record",       ["python", ".github/hooks/scripts/remind-record.py", "--selftest"], False, False),
    ("draft-learnings",     ["python", ".github/hooks/scripts/draft-learnings.py", "--selftest"], False, False),
    ("remind-session-boundary", ["python", ".github/hooks/scripts/remind-session-boundary.py", "--selftest"], False, False),
    ("external-lock-selftest", ["python", "tools/external_lock.py", "--selftest"], False, False),
    ("external-lock-check", ["python", "tools/external_lock.py", "--check"], False, False),
    ("mark-abnormal-stop",  ["python", ".github/hooks/scripts/mark-abnormal-stop.py", "--selftest"], False, False),
    ("log-instructions-loaded", ["python", ".github/hooks/scripts/log-instructions-loaded.py", "--selftest"], False, False),
    ("log-model-switch",    ["python", ".github/hooks/scripts/log-model-switch.py", "--selftest"], False, False),
    ("_log",                ["python", ".github/hooks/scripts/_log.py", "--selftest"], False, False),
    ("guard-subagent-output", ["python", ".github/hooks/scripts/guard-subagent-output.py", "--selftest"], False, False),
    ("hook-metrics",        ["python", "tools/hook-metrics.py", "--selftest"], False, False),
    ("subagent-adapters",   ["python", "tools/subagent_adapters.py", "--selftest"], False, False),
    ("watchdog-continue",   ["python", ".github/hooks/scripts/watchdog-continue.py", "--selftest"], False, False),
    ("gate-status",         ["python", "tools/gate_status.py", "--selftest"], False, False),
    ("golden-eval",         ["python", "tools/golden-eval.py", "--selftest"], False, False),
    ("trace-check",         ["python", "tools/trace-check.py", "--selftest"], False, False),
    ("questionnaire",       ["python", "tools/questionnaire.py", "--selftest"], False, False),
    ("sync-harness",        ["python", "tools/sync-harness.py", "--selftest"], False, False),
    ("intake-app",          ["python", "tools/intake-app.py", "--selftest"], False, False),
    ("platform-requirements", ["python", "tools/platform_requirements.py", "--selftest"], False, False),
    ("doctor-selftest",     ["python", "tools/doctor.py", "--selftest"], False, False),
    ("doctor",              ["python", "tools/doctor.py", "--no-probe"], False, False),
    ("e2e-run",             ["python", "tools/e2e-run.py", "--selftest"], False, False),
    ("check-todo-cli",      ["python", "evaluation/tasks/todo-cli/check.py", "--selftest"], False, False),
    ("check-expense-webapp", ["python", "evaluation/tasks/expense-webapp/check.py", "--selftest"], False, False),
    ("eval-report-selftest", ["python", "tools/eval-report.py", "--selftest"], False, False),
    ("eval-report-check",   ["python", "tools/eval-report.py", "--report", "--check"], False, False),
    # ---- windows ジョブ相当 ----
    ("ps1-bom",             ["python", "-c",
        "import pathlib,sys; bad=[str(p) for p in sorted(pathlib.Path('.').rglob('*.ps1')) "
        "if '.git' not in p.parts and not p.read_bytes().startswith(b'\\xef\\xbb\\xbf')]; "
        "print(*(['BOM missing: '+b for b in bad] or ['ps1 BOM OK']), sep='\\n'); sys.exit(1 if bad else 0)"],
        True, False),
    ("sh-lf",               ["python", "-c",
        "import pathlib,sys; bad=[str(p) for p in sorted(pathlib.Path('.').rglob('*.sh')) "
        "if '.git' not in p.parts and b'\\r' in p.read_bytes()]; "
        "print(*(['CR found: '+b for b in bad] or ['sh LF OK']), sep='\\n'); sys.exit(1 if bad else 0)"],
        True, False),
    ("selftest-ps1",        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                             "-File", ".github/hooks/scripts/selftest.ps1"], True, False),
    ("ps1-hooks-run",       ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                             "-File", str(HERE / "ps1-hooks-run.ps1")], False, False),
    # ---- CONTRIBUTING.md 推奨（CI 外）: 3.12 限定構文の事前検出 ----
    ("py311-compile",       ["python", "-m", "compileall", "-q", "-f", "tools", ".github/hooks/scripts", "evaluation"],
                             True, False),
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quick", action="store_true", help="主要検査だけ")
    ap.add_argument("--only", help="カンマ区切りの検査名")
    ap.add_argument("--list", action="store_true", help="検査一覧を表示")
    ap.add_argument("--with-claude", action="store_true", help="claude CLI を要する検査も含める")
    ap.add_argument("--fail-fast", action="store_true", help="最初の失敗で止める")
    args = ap.parse_args()

    if not (HARNESS_ROOT / "tools" / "validate-harness.py").exists():
        print(f"エラー: HARNESS_ROOT={HARNESS_ROOT} にハーネスが見つかりません。", file=sys.stderr)
        return 2

    selected = STEPS
    if args.quick:
        selected = [s for s in selected if s[2]]
    if args.only:
        names = {n.strip() for n in args.only.split(",") if n.strip()}
        unknown = names - {s[0] for s in STEPS}
        if unknown:
            print(f"エラー: 不明な検査名 {sorted(unknown)}", file=sys.stderr)
            return 2
        selected = [s for s in STEPS if s[0] in names]
    if not args.with_claude:
        selected = [s for s in selected if not s[3]]

    if args.list:
        for name, argv, quick, needs_claude in selected:
            tag = ("quick " if quick else "      ") + ("claude" if needs_claude else "")
            print(f"{name:28s} {tag:12s} {' '.join(argv)}")
        return 0

    # 保守モードの状態（settings.json.locked の有無）を先に知らせる
    locked = HARNESS_ROOT / ".claude" / "settings.json.locked"
    print(f"HARNESS_ROOT = {HARNESS_ROOT}")
    print(f"python       = {PY} ({sys.version.split()[0]})")
    print("保守モード   = " + ("【ON】 settings.json.locked あり（validate の deny 照合が崩れる）" if locked.exists() else "OFF"))
    try:
        br = subprocess.run(["git", "branch", "--show-current"], cwd=HARNESS_ROOT, capture_output=True, text=True).stdout.strip()
        st = subprocess.run(["git", "status", "--short"], cwd=HARNESS_ROOT, capture_output=True, text=True).stdout
        print(f"git          = branch {br or '(detached)'}, 未コミット {len(st.splitlines())} 件")
    except Exception:
        pass
    print("-" * 72)

    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    results: list[tuple[str, int, float]] = []
    for name, argv, _, _ in selected:
        cmd = [PY if a == "python" else a for a in argv]
        t0 = time.time()
        print(f"\n### {name} [{time.strftime('%H:%M:%S')}]: {' '.join(argv)}", flush=True)
        try:
            # stdin は切り離す（CI と同じく入力なし）。パイプを継承させると stdin を読むフック
            # （inject-progress.ps1 等）が EOF を待って止まる
            rc = subprocess.run(cmd, cwd=HARNESS_ROOT, env=env, stdin=subprocess.DEVNULL,
                                timeout=TIMEOUTS.get(name, DEFAULT_TIMEOUT)).returncode
        except FileNotFoundError as e:
            print(f"(実行できません: {e})")
            rc = 127
        except subprocess.TimeoutExpired:
            print(f"(タイムアウト {TIMEOUTS.get(name, DEFAULT_TIMEOUT)}s: 子プロセスを強制終了)")
            rc = 124
        dt = time.time() - t0
        results.append((name, rc, dt))
        print(f"### {name}: {'OK' if rc == 0 else f'FAIL (exit={rc})'} [{dt:.1f}s]", flush=True)
        if rc != 0 and args.fail_fast:
            break

    print("\n" + "=" * 72)
    failed = [r for r in results if r[1] != 0]
    for name, rc, dt in results:
        print(f"{'OK  ' if rc == 0 else 'FAIL'}  {name:28s} {dt:6.1f}s")
    print("=" * 72)
    print(f"{len(results) - len(failed)} OK / {len(failed)} FAIL / {len(results)} 実行")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
