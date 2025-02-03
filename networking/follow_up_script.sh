#!/bin/bash

# Define arguments
RUN_SAVE_DIR="./follow_up_run"
UNKNOWN_WORDS_PATH="./using_unknown_words.txt"
MANUAL_CORRECTIONS_PATH="./using_results.json"

# Run Python script with arguments
python3 word_fixing_by_char.py "$RUN_SAVE_DIR" "$UNKNOWN_WORDS_PATH" "$MANUAL_CORRECTIONS_PATH" 
