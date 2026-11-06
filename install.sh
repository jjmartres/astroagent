#!/bin/sh
# Link the astroagent skills into ~/.claude/skills (read by Claude Code and by OpenCode).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
for skill in astro-processing nebulis; do
  target="$dest/$skill"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "skip $skill: $target exists and is not a link (move it away first)" >&2
    continue
  fi
  ln -sfn "$here/skills/$skill" "$target"
  echo "linked $target -> $here/skills/$skill"
done
chmod +x "$here/skills/nebulis/scripts/nebulis.py"
if [ ! -f "$HOME/.config/nebulis/env" ]; then
  echo "next: create ~/.config/nebulis/env from config/nebulis.env.example (chmod 600)"
fi
