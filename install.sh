#!/bin/bash

# This script makes the timetrack CLI available as 'track' from anywhere.

# 1. Define the source and destination paths
CLI_ENTRY_POINT="project/timetrack/cli.py"
DEST_DIR="$HOME/.local/bin"
DEST_FILE="$DEST_DIR/track"
VENV_PYTHON="`pwd`/.venv/bin/python"

# 2. Create the destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# 3. Create a launcher script
echo "#!/bin/bash" > "$DEST_FILE"
echo "cd `pwd`" >> "$DEST_FILE"
echo "$VENV_PYTHON -m project.timetrack.cli \"\$@\"" >> "$DEST_FILE"

# 4. Make the script executable
chmod +x "$DEST_FILE"

# 5. Add a message for the user
echo "✅ Installation complete!"
echo "You can now use the 'track' command from anywhere in your terminal."
echo "Try running: track status"
