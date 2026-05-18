#!/bin/bash
set -e

SESSION=rdt
rm -f logs/router_*.log

tmux new-session -d -s "$SESSION" -x 220 -y 50

tmux send-keys -t "$SESSION" "python3 main.py 1" Enter
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION" "python3 main.py 2" Enter
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION" "python3 main.py 3" Enter
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION" "python3 main.py 4" Enter
tmux split-window -h -t "$SESSION"
tmux send-keys -t "$SESSION" "python3 main.py 5" Enter
tmux select-layout -t "$SESSION" tiled

exec tmux attach -t "$SESSION"
