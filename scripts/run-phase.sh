#!/usr/bin/env bash
# ハーネスを適用した使い捨てプロジェクトで、1 フェーズ（1 発話）をヘッドレス実行して記録する。
#   usage: scripts/run-phase.sh <workdir> <label> "<prompt>" [--resume <session-id>]
# 出力: <workdir>/../logs/<label>.jsonl（stream-json 全文）、<label>.result.txt（最終応答）、<label>.session（session id）
# 条件は evaluation/results/elicitation/todo-app-01-20260923.json の手動計測と同型
# （acceptEdits・allowedTools 6+2・max-turns 80・予算上限・ユーザースコープの model/effort 上書きを遮断）。
set -u
# Git Bash が "/01-..." のような先頭スラッシュの引数を Windows パスに変換するのを止める
export MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL="*"
WORKDIR="$1"; LABEL="$2"; PROMPT="$3"; shift 3
LOGDIR="$(dirname "$WORKDIR")/logs"; mkdir -p "$LOGDIR"
SID=""
if [[ "${1:-}" == "--resume" ]]; then SID="$2"; fi
NEW_SID="$(python -c 'import uuid;print(uuid.uuid4())')"

# 入れ子セッション由来・ユーザースコープ由来の環境変数を外す（e2e-run.py の ENV_SCRUB と同じ）
for v in CLAUDECODE CLAUDE_CODE_SESSION_ID CLAUDE_CODE_HOST_SESSION_ID CLAUDE_PID CLAUDE_CODE_CHILD_SESSION \
         CLAUDE_CODE_MESSAGING_SOCKET CLAUDE_CODE_MESSAGING_TOKEN CLAUDE_CODE_ENTRYPOINT CLAUDE_EFFORT \
         CLAUDE_CODE_EFFORT_LEVEL CLAUDE_CODE_SUBAGENT_MODEL CLAUDE_CODE_SUBAGENT_MODEL_FORCE ANTHROPIC_MODEL \
         ANTHROPIC_SMALL_FAST_MODEL CLAUDE_CODE_MAX_OUTPUT_TOKENS MAX_THINKING_TOKENS CLAUDE_CODE_SAFE_MODE \
         CLAUDE_CONFIG_DIR CLAUDE_CODE_PROJECT_DIR_NAME; do unset "$v"; done

ARGS=(-p "$PROMPT" --permission-mode acceptEdits
      --allowedTools "Bash(python:*)" "Bash(py:*)" "Bash(git:*)" "PowerShell(python:*)" "PowerShell(py:*)" "PowerShell(git:*)" "Agent" "Skill"
      --max-turns 80 --max-budget-usd 12
      --output-format stream-json --verbose --setting-sources project,local --strict-mcp-config)
if [[ -n "$SID" ]]; then ARGS+=(--resume "$SID"); echo "$SID" > "$LOGDIR/$LABEL.session"
else ARGS+=(--session-id "$NEW_SID"); echo "$NEW_SID" > "$LOGDIR/$LABEL.session"; fi

echo "[$(date '+%H:%M:%S')] start $LABEL in $WORKDIR" | tee "$LOGDIR/$LABEL.status"
( cd "$WORKDIR" && claude "${ARGS[@]}" ) > "$LOGDIR/$LABEL.jsonl" 2> "$LOGDIR/$LABEL.stderr"
RC=$?
echo "[$(date '+%H:%M:%S')] exit $RC" | tee -a "$LOGDIR/$LABEL.status"

python - "$LOGDIR/$LABEL.jsonl" "$LOGDIR/$LABEL.result.txt" <<'EOF'
import json, sys
src, dst = sys.argv[1], sys.argv[2]
res = None; init = None; n_assist = 0
for line in open(src, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line: continue
    try: o = json.loads(line)
    except Exception: continue
    t = o.get("type")
    if t == "system" and o.get("subtype") == "init": init = o
    elif t == "assistant": n_assist += 1
    elif t == "result": res = o
with open(dst, "w", encoding="utf-8") as f:
    if init: f.write(f"model={init.get('model')} version={init.get('claude_code_version') or init.get('version')} skills={len(init.get('skills') or [])} agents={len(init.get('agents') or [])}\n")
    if res:
        f.write(f"subtype={res.get('subtype')} is_error={res.get('is_error')} turns={res.get('num_turns')} cost_usd={res.get('total_cost_usd')} duration_s={round((res.get('duration_ms') or 0)/1000)} assistant_msgs={n_assist}\n")
        f.write("---- result ----\n"); f.write(str(res.get("result")) + "\n")
    else:
        f.write("(no result record)\n")
print(open(dst, encoding="utf-8").read()[:1500])
EOF
