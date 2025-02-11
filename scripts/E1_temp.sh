#!/bin/bash
NAME="E1"
# Directories and log file for E2
SOURCE_DIR="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/data/gcloud_splits/unmodified_text/$NAME/"
DEST_DIR="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/new_clean_text/$NAME"
LOG_FILE="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/logs/$NAME.log"
PYTHON_SCRIPT="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/python_scripts/${NAME}.py"

# Call the common script
/Users/BeckyMarcusMacbook/Thesis/TextCleaning/scripts/run_pipeline.sh "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" "$PYTHON_SCRIPT"