# sdlc-harness-dev — ハーネス本体の保守プロジェクト

このプロジェクトは **ハーネス本体（テンプレート）そのものを改修する** ための作業場所。
対象リポジトリ（以下 HARNESS_ROOT）: `D:\vscode-worspace\CreateAppl`
（GitHub: n-ima/copilot-sdlc-harness。ここにはアプリのコードは無い）

ここはアプリ開発プロジェクトではない。HARNESS_ROOT の `AGENTS.md`・フェーズコマンド
（/01〜/99）・受付ルーチンは **このプロジェクトには適用しない**。頼まれたのは
「ハーネスを直す」仕事であり、「ハーネスを使ってアプリを作る」仕事ではない。

## なぜ別プロジェクトから保守するのか

- Claude Code の `.claude/settings.json`（hooks・permissions.deny・statusLine）と `CLAUDE.md` は
  **起動ディレクトリ（cwd）からだけ** 読まれる。`permissions.additionalDirectories` で追加した
  ディレクトリからは設定・hooks・CLAUDE.md・commands・skills のいずれも読まれない
  （公式: permissions「Additional directories grant file access, not configuration」）。
- したがって HARNESS_ROOT 自身を開くと、自己防衛ガード（deny 約60件 + PreToolUse フック）と
  UserPromptSubmit/Stop フック・常駐 AGENTS.md が保守作業の邪魔をするが、ここから開けば効かない。
- これは HARNESS_ROOT の設計上は「ガード迂回」の経路であり、DECISIONS.md に前例として記録済み
  （「本適用はハーネス外のセッション（別ディレクトリを起点とする Claude Code）から実施した。
  … ユーザーの明示指示なしにこの経路で保護対象を編集してはならない」）。
  **保護対象（AGENTS.md / CLAUDE.md / .github/agents,hooks,prompts,instructions,workflows /
  .claude/settings.json / request-routing・gate-check スキル / PLATFORM.md / model-policy.yml /
  テンプレート）を編集するのは、ユーザーがそのセッションで明示的に指示したときだけ。**
- `--add-dir` / `/add-dir` は使わない（その経路だと HARNESS_ROOT の skills / commands / agents が
  このセッションに読み込まれる）。追加は `.claude/settings.json` の `additionalDirectories` で済んでいる。
- `tools/harness-maintenance.py --on` は **実行しない**（人間専用 + TTY 確認。ここからは不要。
  ON のまま残ると validate の deny 三面照合が崩れ、生成物系 ERROR が出る）。
  作業前に `python tools/harness-maintenance.py` で OFF を確認する（`scripts/check.py` も表示する）。

## 作業の流れ

1. **CONTRIBUTING.md と DECISIONS.md（HARNESS_ROOT）を先に読む。** 変更対象に関係する D 記録が
   ないか確認し、同じ議論の再演・一度直したバグの再導入を避ける。
2. HARNESS_ROOT で **ブランチを切って** 作業する（main 直コミットはしない）。
3. **正は 1 か所**（`AGENTS.md` + `.github/`）。以下は生成物なので手で編集せず、生成器を回す:
   - `.claude/commands|agents|rules|skills`、`.claude-plugin/*`、`.github/skills/<nn>-*/`、
     `.github/copilot/settings.json`、モデル対照表 → `python tools/generate-adapters.py`
     （`--check` で差分検査。`permissions.deny` の `Agent(model:…)` だけは `--print-deny` で人が反映）
   - README の対応表・統計タイル・件数文言 → `python tools/gen-docs.py --apply`（`--check` で検査）
4. **検証**: `.venv\Scripts\python scripts\check.py --quick`（作業中）→ `scripts\check.py`（コミット前。
   CI と同等）。検査項目の正は `.github/workflows/harness-ci.yml`。
5. **記録**: `DECISIONS.md` に D 記録（根拠・捨てた選択肢・検証結果）、`CHANGELOG.md`、
   必要なら `audits/PROPOSALS.md` の状態更新。
6. ブランチにコミット。**push・tag・release はユーザーの指示があるときだけ**（tag は人が付ける）。
   「完了」と言う前に、承認待ちの外部反映（push 等）が残っていないか明示する。

## 規約

- Python は **3.11**（`.venv`。CI と同じ版。3.12 限定構文を使うと CI だけが落ちる）。
  ハーネスのツールは `.venv\Scripts\python` で、cwd を HARNESS_ROOT にして実行する。
- `.sh` は LF、`.ps1` は BOM 付き UTF-8（CI の windows ジョブが機械検査）。
- フック `.sh` と `.ps1` は同一判定を保つ（片方だけ直さない）。selftest.sh / selftest.ps1 に回帰テストを足す。
- コミットしないもの: `.github/hooks/logs/`、`.claude/settings.json.locked`、`__pycache__/`。
- サブエージェントに haiku を使わない（HARNESS_ROOT の方針と同じ。本プロジェクトの deny で機械化）。
- HARNESS_ROOT のファイルは絶対パスで指す（相対パスはこのプロジェクトのルート基準になる）。
