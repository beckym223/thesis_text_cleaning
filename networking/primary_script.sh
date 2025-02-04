#!/bin/bash

# Capture the directory where the script is executed from
CURRENT_DIR=$(pwd)

# Define arguments
RUN_SAVE_DIR="networking/primary_run"
UNKNOWN_WORDS_PATH="manual_work/E2/problematic_unfixed"
MANUAL_CORRECTIONS_PATH="manual_work/corrections.json"
SCRIPT_PATH="networking/word_fixing_by_char.py"


# Get absolute paths before passing them to Python
ABS_RUN_SAVE_DIR=$(realpath --relative-to="$CURRENT_DIR" "$RUN_SAVE_DIR")
ABS_UNKNOWN_WORDS_PATH=$(realpath --relative-to="$CURRENT_DIR" "$UNKNOWN_WORDS_PATH")
ABS_MANUAL_CORRECTIONS_PATH=$(realpath --relative-to="$CURRENT_DIR" "$MANUAL_CORRECTIONS_PATH")

ABS_SCRIPT_PATH=$(realpath --relative-to="$CURRENT_DIR" "$SCRIPT_PATH")

# echo "$ABS_RUN_SAVE_DIR"
# echo "$ABS_UNKNOWN_WORDS_PATH"
# echo "$MANUAL_CORRECTIONS_PATH"

# Run the Python script, passing the absolute paths
python3 "$ABS_SCRIPT_PATH" "$ABS_RUN_SAVE_DIR" "$ABS_UNKNOWN_WORDS_PATH" "$ABS_MANUAL_CORRECTIONS_PATH" --read_dir

