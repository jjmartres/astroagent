#!/bin/sh
# Link the astroagent skills into ~/.claude/skills (read by Claude Code and by OpenCode).
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
for skill in astro-processing astro-project nebulis; do
  target="$dest/$skill"
  if [ -e "$target" ] && [ ! -L "$target" ]; then
    echo "skip $skill: $target exists and is not a link (move it away first)" >&2
    continue
  fi
  ln -sfn "$here/skills/$skill" "$target"
  echo "linked $target -> $here/skills/$skill"
done
chmod +x "$here/skills/nebulis/scripts/nebulis.py" "$here/skills/astro-project/scripts/astro_project.py"
if [ ! -f "$HOME/.config/astroagent/env" ] && [ -z "${ASTROAGENT_NEBULIS_API_KEY:-}" ]; then
  echo "next: set ASTROAGENT_NEBULIS_URL and ASTROAGENT_NEBULIS_API_KEY, or create ~/.config/astroagent/env from config/astroagent.env.example (chmod 600)"
fi
