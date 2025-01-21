#!/bin/bash

# Usage: ./test_pipeline.sh <scenario>

SCENARIO=$1
SOURCE_DIR="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/testing/.test_source"
DEST_DIR="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/testing/test_dest"
LOG_FILE="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/testing/test_log.log"
PYTHON_SCRIPT="/Users/BeckyMarcusMacbook/Thesis/TextCleaning/python_scripts/mock_cleaning.py"

# Ensure directories exist and prepare test files
mkdir -p "$SOURCE_DIR" "$DEST_DIR"

# Clear previous logs and destination
> "$LOG_FILE"
rm -rf "$DEST_DIR/*"

echo "Running test scenario: $SCENARIO"

case "$SCENARIO" in
    success)
        echo "Simulating a successful pipeline run..."
        /Users/BeckyMarcusMacbook/Thesis/TextCleaning/scripts/run_pipeline.sh -b test "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" "$PYTHON_SCRIPT" 
        ;;
    failure)
        echo "Simulating a failed pipeline run..."
        /Users/BeckyMarcusMacbook/Thesis/TextCleaning/scripts/run_pipeline.sh -b "test" "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" "$PYTHON_SCRIPT" --fail 
        ;;
    no_commit)
        echo "Simulating changes made but not committed..."
        /Users/BeckyMarcusMacbook/Thesis/TextCleaning/scripts/run_pipeline.sh -b "test" "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" "$PYTHON_SCRIPT" --no-commit
        ;;
    *)
        echo "Invalid scenario. Choose from: success, failure, no_commit"
        exit 1
        ;;
esac

echo "Test completed. Check the log file for details: $LOG_FILE"
