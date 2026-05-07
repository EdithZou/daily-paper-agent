#!/usr/bin/env bash
# Install a launchd job that runs the daily paper agent at 9 AM.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
USERNAME="$(whoami)"
LABEL="com.${USERNAME}.daily-paper-agent"
PLIST_DEST="$HOME/Library/LaunchAgents/${LABEL}.plist"
TEMPLATE="$SCRIPT_DIR/com.user.daily-paper-agent.plist.template"

echo "Installing launchd job: $LABEL"
echo "Project directory: $PROJECT_DIR"

# Create LaunchAgents directory if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Substitute placeholders
sed \
  -e "s|__PROJECT_DIR__|$PROJECT_DIR|g" \
  -e "s|__USERNAME__|$USERNAME|g" \
  "$TEMPLATE" > "$PLIST_DEST"

echo "Plist written to: $PLIST_DEST"

# Ensure the run script is executable
chmod +x "$PROJECT_DIR/scripts/run_daily.sh"

# Unload existing job if present, ignore errors
launchctl unload "$PLIST_DEST" 2>/dev/null || true

# Load the new job
launchctl load "$PLIST_DEST"

echo ""
echo "Done! The agent will run every day at 20:00 (8 PM Singapore time)."
echo ""
echo "Useful commands:"
echo "  Check status:   launchctl list | grep $LABEL"
echo "  Run now:        launchctl start $LABEL"
echo "  Uninstall:      launchctl unload $PLIST_DEST && rm $PLIST_DEST"
echo "  View logs:      tail -f $PROJECT_DIR/logs/launchd.out.log"
