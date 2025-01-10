#!/bin/bash
NAME="E1"
# Directories and log file for E2
SOURCE_DIR="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/data/groups/$NAME/texts"
DEST_DIR="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/clean_text/$NAME"
LOG_FILE="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/cleaning_by_group/logs/$NAME.log"
PYTHON_SCRIPT="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/python_scripts/${NAME}.py"

# Call the common script
/Users/BeckyMarcusMacbook/Thesis/TextCleaning/scripts/run_pipeline.sh "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" "$PYTHON_SCRIPT"
/Users/BeckyMarcusMacbook/Thesis/TextCleaning/python_scripts/E1.py