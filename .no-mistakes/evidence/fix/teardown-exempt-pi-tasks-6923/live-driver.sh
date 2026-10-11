#!/usr/bin/env bash
set -eu
ROOT=$PWD
export PATH="$ROOT/.test-treehouse/.test-treehouse:$PATH"
unset FM_ROOT_OVERRIDE FM_STATE_OVERRIDE FM_DATA_OVERRIDE FM_CONFIG_OVERRIDE FM_PROJECTS_OVERRIDE FM_GATE_REFUSE_BYPASS TMUX
mkdir -p .test-live
trap 'tmux -S "$ROOT/.t" kill-server 2>/dev/null || true; rm -rf "$ROOT/.test-live"; rm -f "$ROOT/.t"' EXIT
for scenario in scratch sibling tracked staged unlanded; do
 LAB="$ROOT/.test-live/$scenario"
 bin/fm-lab-home.sh create "$LAB"
 export FM_HOME="$LAB" TREEHOUSE_ROOT="$LAB/pool"
 git init -q -b main "$LAB/projects/demo"
 PROJ="$LAB/projects/demo"
 git -C "$PROJ" -c user.name=Test -c user.email=test@example.invalid commit -q --allow-empty -m baseline
 git -C "$PROJ" update-ref refs/remotes/origin/main HEAD
 WT=$(cd "$PROJ" && treehouse get --lease --no-fetch)
 git -C "$WT" checkout -q -b fm/proof
 mkdir -p "$WT/.pi/tasks/uuid"
 printf '{}\n' > "$WT/.pi/tasks/uuid/state.json"
 case "$scenario" in
 sibling) mkdir -p "$WT/.pi/extensions"; echo custom > "$WT/.pi/extensions/custom.ts" ;;
 tracked|staged) git -C "$WT" add .pi/tasks; git -C "$WT" -c user.name=Test -c user.email=test@example.invalid commit -q -m tracked; git -C "$WT" update-ref refs/remotes/origin/main HEAD; echo edit >> "$WT/.pi/tasks/uuid/state.json"; if [ "$scenario" = staged ]; then git -C "$WT" add .pi/tasks; fi ;;
 unlanded) echo work > "$WT/feature"; git -C "$WT" add feature; git -C "$WT" -c user.name=Test -c user.email=test@example.invalid commit -q -m unlanded ;;
 esac
 tmux -S "$ROOT/.t" -f /dev/null new-session -d -s fm-lab-proof -n fm-proof 'sleep 600'
 export TMUX="$ROOT/.t,0,0"
 printf 'window=fm-lab-proof:fm-proof\nspawn_gen=live-proof\nworktree=%s\nproject=%s\nkind=ship\nmode=local-only\nharness=codex\n' "$WT" "$PROJ" > "$LAB/state/proof.meta"
 echo "SCENARIO $scenario BEFORE"
 git -C "$WT" status --porcelain --untracked-files=all
 rc=0
 bin/fm-teardown.sh proof || rc=$?
 echo "RESULT $scenario exit=$rc metadata=$([ -f "$LAB/state/proof.meta" ] && echo retained || echo removed)"
 if [ "$scenario" = scratch ]; then [ "$rc" = 0 ]; [ ! -f "$LAB/state/proof.meta" ]; else [ "$rc" = 1 ]; [ -f "$LAB/state/proof.meta" ]; git -C "$WT" status --porcelain --untracked-files=all; fi
 tmux -S "$ROOT/.t" kill-server 2>/dev/null || true
 done
