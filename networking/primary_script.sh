#!/bin/bash

# Define arguments
RUN_SAVE_DIR="./primary_run"
UNKNOWN_WORDS_PATH="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/manual_work/E2/problematic_unfixed"
MANUAL_CORRECTIONS_PATH="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/manual_work/corrections.json"

# Run Python script with arguments
python3 word_fixing_by_char.py "$RUN_SAVE_DIR" "$UNKNOWN_WORDS_PATH" "$MANUAL_CORRECTIONS_PATH" --read_dir
