#!/bin/zsh
#
# ACE-Step for Mac - double-click launcher.
#
# You do not need to edit this file. It works out where it is, finds
# ACE-Step's virtual environment, starts the app and opens it in your
# browser. If ACE-Step lives somewhere unusual on your machine, set
# ACESTEP_REPO before running it - see INSTALL.md.
#
# To close the app: close the Terminal window this opens, or press
# Control-C in it.

# --- where things are -------------------------------------------------------

# The folder this launcher is sitting in. This is how the app can be moved
# anywhere on the disk and still start.
HERE="${0:A:h}"
APP="$HERE/acestep_app.py"

# Where ACE-Step 1.5 itself is installed. INSTALL.md puts it here.
REPO="${ACESTEP_REPO:-$HOME/AceStep/ACE-Step-1.5}"
VENV="$REPO/.venv/bin/activate"

# Where the model weights are downloaded to, the first time you render.
CKPT="${ACESTEP_CHECKPOINTS_DIR:-$HOME/AceStep/checkpoints}"

PORT="${ACESTEP_PORT:-7873}"
URL="http://127.0.0.1:$PORT"

# ACE-Step's own macOS scripts set these. This app calls the same code
# without going through those scripts, so it sets them too.
export ACESTEP_LM_BACKEND=mlx
export ACESTEP_REPO="$REPO"
export ACESTEP_CHECKPOINTS_DIR="$CKPT"
export PYTORCH_ENABLE_MPS_FALLBACK=1

# --- checks, with a readable message for each failure -----------------------

if [ ! -f "$APP" ]; then
  echo "Can't find acestep_app.py next to this launcher."
  echo "Looked for: $APP"
  echo ""
  echo "Keep launch_acestep.command and acestep_app.py in the same folder."
  read -n 1 -s -r -p "Press any key to close this window..."
  exit 1
fi

if [ ! -f "$VENV" ]; then
  echo "Can't find ACE-Step's virtual environment."
  echo "Looked for: $VENV"
  echo ""
  echo "That means ACE-Step 1.5 is not installed yet, or it is installed"
  echo "somewhere else on this Mac."
  echo ""
  echo "  - Not installed?  Open INSTALL.md in this folder and follow it once."
  echo "  - Installed elsewhere?  Tell this launcher where, like this:"
  echo "        export ACESTEP_REPO=/your/path/to/ACE-Step-1.5"
  read -n 1 -s -r -p "Press any key to close this window..."
  exit 1
fi

# Already running? Just bring it back up rather than starting a second copy.
if lsof -i tcp:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "ACE-Step for Mac is already running on port $PORT."
  echo "Reopening it in your browser."
  open "$URL"
  read -n 1 -s -r -p "Press any key to close this window..."
  exit 0
fi

# --- go ---------------------------------------------------------------------

source "$VENV"
cd "$HERE"

echo ""
echo "  ACE-Step for Mac"
echo "  ----------------------------------------------------------------"
echo "  Starting up. This window is the log: keep it open while you work."
echo ""
echo "  The FIRST render downloads several gigabytes of model weights into"
echo "    $CKPT"
echo "  so the first one sits there a long time with nothing apparently"
echo "  happening. That is normal, and it happens only once."
echo ""
echo "  Your browser will open in a few seconds at $URL"
echo "  ----------------------------------------------------------------"
echo ""

(sleep 4 && open "$URL") &

python3 "$APP"

echo ""
read -n 1 -s -r -p "ACE-Step for Mac has stopped. Press any key to close this window..."
