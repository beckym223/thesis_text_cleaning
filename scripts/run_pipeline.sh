if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <source_dir> <dest_dir> <log_file> <python_script>"
    exit 1
fi

# Arguments
SOURCE_DIR="$1"
DEST_DIR="$2"
LOG_FILE="$3"
PYTHON_SCRIPT="$4"

# Get the current branch
CURRENT_BRANCH=$(git branch --show-current)

# Generate a unique branch name
BRANCH_NAME="pipeline-run-$(date +'%Y%m%d%H%M%S')"

# Create and switch to the new branch, setting its upstream to the current branch
git checkout -b "$BRANCH_NAME" --track "$CURRENT_BRANCH"

# Run the specified Python cleaning script
python "$PYTHON_SCRIPT" "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" true

# Check if the script succeeded
if [ $? -eq 0 ]; then
    # Commit changes to the new branch
    git add "$DEST_DIR/."
    git commit -m "Pipeline run completed on $BRANCH_NAME"
    echo "Pipeline run completed. Changes committed to branch: $BRANCH_NAME"
else
    # Preserve the branch for debugging
    echo "Pipeline run failed. Changes remain in branch: $BRANCH_NAME"
    echo "Switch back to the original branch with 'git checkout $CURRENT_BRANCH' to continue work."
    exit 1
fi

# Output the branch for manual merge
echo "Changes have been committed to branch: $BRANCH_NAME"

# Output the branch for manual merge
echo "Changes have been committed to branch: $BRANCH_NAME"

# Ask the user if they want to run the merge and cleanup immediately
read -p "Do you want to merge and clean up now? (y/n): " user_input

# Check if the user typed 'y'
if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
    # Run the merge and cleanup script immediately
    ./scripts/merge_and_cleanup.sh "$BRANCH_NAME"
else
    # Print instructions for manual merge and cleanup
    echo "After reviewing changes, run 'scripts/merge_and_cleanup.sh $BRANCH_NAME' to merge changes and delete the temporary branch."
fi