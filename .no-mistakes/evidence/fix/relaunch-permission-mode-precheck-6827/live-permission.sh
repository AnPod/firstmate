#!/usr/bin/env bash
set -u
LAB=$(mktemp -d "${TMPDIR:-/tmp}/fm-lab.XXXXXX")
cleanup() { TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab kill-server 2>/dev/null || true; rm -rf "$LAB"; }
trap cleanup EXIT
bin/fm-lab-home.sh create "$LAB"
mkdir -p "$LAB/tmux" "$LAB/data/permission"
env -u NO_MISTAKES_GATE -u FM_GATE_REFUSE_BYPASS -u FM_ROOT_OVERRIDE -u FM_STATE_OVERRIDE -u FM_DATA_OVERRIDE -u FM_CONFIG_OVERRIDE -u FM_PROJECTS_OVERRIDE -u CLAUDECODE TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab new-session -d -s primary -x 120 -y 40 -c "$PWD" -e FM_HOME="$LAB" claude
TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab rename-window -t primary:0 fm-permission
sleep 5
TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab capture-pane -p -t primary
cat > "$LAB/state/permission.meta" <<EOF
window=primary:fm-permission
endpoint_task_id=permission
backend=tmux
worktree=$PWD
project=$PWD
harness=claude
kind=ship
mode=no-mistakes
yolo=off
model=default
effort=default
EOF
cp "$LAB/state/permission.meta" "$LAB/before.meta"
printf '# Disposable relaunch proof\n' > "$LAB/data/permission/brief.md"
before=$(TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab list-panes -t primary -F '#{pane_pid}:#{pane_current_command}')
for variant in bogus directory dangling codex; do
  rm -rf "$LAB/config/claude-permission-mode"
  case "$variant" in
    directory) mkdir "$LAB/config/claude-permission-mode" ;;
    dangling) ln -s "$LAB/nonexistent" "$LAB/config/claude-permission-mode" ;;
    *) printf 'bogus\n' > "$LAB/config/claude-permission-mode" ;;
  esac
  args=(); [ "$variant" != codex ] || args=(--harness codex)
  printf '\nSCENARIO %s\n' "$variant"
  env -u FM_GATE_REFUSE_BYPASS -u FM_ROOT_OVERRIDE -u FM_STATE_OVERRIDE -u FM_DATA_OVERRIDE -u FM_CONFIG_OVERRIDE -u FM_PROJECTS_OVERRIDE FM_HOME="$LAB" TMUX_TMPDIR="$LAB/tmux" TMUX="$LAB/tmux/tmux-$(id -u)/fm-lab,0,0" bin/fm-control.sh permission relaunch "${args[@]}" --note 'Disposable permission-mode refusal proof'
  rc=$?
  after=$(TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab list-panes -t primary -F '#{pane_pid}:#{pane_current_command}')
  printf 'exit=%s agent-before=%s agent-after=%s\n' "$rc" "$before" "$after"
  cmp "$LAB/before.meta" "$LAB/state/permission.meta" && echo 'task metadata unchanged'
  [ "$rc" = 1 ] && [ "$before" = "$after" ] || exit 1
  [ ! -e "$LAB/state/permission.control-relaunch" ] || exit 1
 done
TMUX_TMPDIR="$LAB/tmux" tmux -L fm-lab capture-pane -p -t primary
