# sdlc-harness-dev

`D:\vscode-worspace\CreateAppl`（copilot-sdlc-harness）**本体を保守するための作業プロジェクト**。
ハーネス自身のディレクトリで Claude Code を開くと自己防衛ガード（deny + フック）と常駐指示が
保守の邪魔をするため、ここを起点にして HARNESS_ROOT を「追加ディレクトリ」として編集する。
Claude Code は追加ディレクトリの設定・hooks・CLAUDE.md を読まないので、ガードや受付ルーチンの
影響を受けずに作業できる（根拠と運用ルールは `CLAUDE.md`）。

## 構成

| パス | 役割 |
|---|---|
| `CLAUDE.md` | Claude Code 向けの運用ルール（保護対象の扱い・生成物・検証・記録） |
| `.claude/settings.json` | `permissions.additionalDirectories` で HARNESS_ROOT を許可。push/tag/reset は ask、haiku サブエージェントは deny |
| `scripts/check.py` | HARNESS_ROOT に対して CI（harness-ci.yml）と同等の検査を一括実行 |
| `scripts/ps1-hooks-run.ps1` | CI の windows ジョブ相当（全 .ps1 フックの実機実行・inject-progress 陽性確認） |
| `.venv/` | Python 3.11（CI と同じ版）+ PyYAML。git 管理外 |

## セットアップ（初回のみ）

```powershell
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r D:\vscode-worspace\CreateAppl\requirements-dev.txt
```

初めてこのフォルダで Claude Code を開いたときは、ワークスペース信頼のダイアログで
追加ディレクトリ（HARNESS_ROOT）を許可する。

## 使い方

```powershell
.venv\Scripts\python scripts\check.py --quick     # 構造検証・生成物差分・フック selftest・BOM/LF・3.11 compile
.venv\Scripts\python scripts\check.py             # CI と同等の全検査
.venv\Scripts\python scripts\check.py --list      # 検査一覧
.venv\Scripts\python scripts\check.py --only validate,selftest-sh
```

HARNESS_ROOT を変えるときは環境変数 `HARNESS_ROOT` と `.claude/settings.json` の
`additionalDirectories` を両方更新する。

## やってはいけないこと

- HARNESS_ROOT で `tools/harness-maintenance.py --on` を実行したまま放置する
  （ここからの保守には不要。ON だと validate が崩れる）。
- `--add-dir` で HARNESS_ROOT を足す（skills / commands / agents がセッションに混入する）。
- 生成物（`.claude/commands` 等）の手編集。`tools/generate-adapters.py` / `tools/gen-docs.py` で再生成する。
