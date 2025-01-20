#!/bin/bash

RUN_EXTRA_COMMAND=false
DEL_BRANCH=true

# Process short options
while getopts "ok" opt; do
    case "$opt" in
        o)
            RUN_EXTRA_COMMAND=true
            ;;
        k)
            DEL_BRANCH=false
            ;;
        *)
            echo "Usage: $0 [-o|--open] [-k|--keep] <source_dir> <dest_dir> <log_file> <python_script>"
            exit 1
            ;;
    esac
done

# Shift past the short options
shift $((OPTIND - 1))

# Process long options manually
while [[ "$1" =~ ^-- ]]; do
    case "$1" in
        --open)
            RUN_EXTRA_COMMAND=true
            ;;
        --keep)
            DEL_BRANCH=false
            ;;
        --help)
            echo "Usage: $0 [-o|--open] [-k|--keep] <source_dir> <dest_dir> <log_file> <python_script>"
            exit 0
            ;;
        *)
            echo "Invalid option: $1"
            exit 1
            ;;
    esac
    shift
done
# # Process short options
# while getopts "ok:" opt; do
#     case "$opt" in
#         o)
#             RUN_EXTRA_COMMAND=true
#             ;;
#         k)
#             DEL_BRANCH=false
#             ;;
#         *)
#             echo "Usage: $0 [-o|--open] [-k|--keep] <source_dir> <dest_dir> <log_file> <python_script>"
#             exit 1
#             ;;
#     esac
# done

# # Shift processed options
# shift $((OPTIND - 1))

# # Process long options manually
# while [[ "$1" =~ ^-- ]]; do
#     case "$1" in
#         --open)
#             RUN_EXTRA_COMMAND=true
#             ;;
#         --keep)
#             DEL_BRANCH=false
#             ;;
#         --threshold)
#             shift
#             THRESHOLD="$1"
#             ;;
#         --help)
#             echo "Usage: $0 [-o|--open] [-k|--keep] <source_dir> <dest_dir> <log_file> <python_script>"
#             exit 0
#             ;;
#         *)
#             echo "Invalid option: $1"
#             exit 1
#             ;;
#     esac
#     shift
# done
# Validate positional arguments
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 [-o|--open] [-k|--keep] <source_dir> <dest_dir> <log_file> <python_script>"
    exit 1
fi

# Arguments
SOURCE_DIR="$1"
DEST_DIR="$2"
LOG_FILE="$3"
PYTHON_SCRIPT="$4"


# Ensure the log file and its directory exist
LOG_DIR=$(dirname "$LOG_FILE")
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi
if [ ! -f "$LOG_FILE" ]; then
    touch "$LOG_FILE"
fi

# Check for unstaged changes in the current branch
if [ -n "$(git status --porcelain)" ]; then
    echo "$(date +'%Y-%m-%d %H:%M:%S') - Unstaged changes detected in the current branch. Aborting pipeline run." >> "$LOG_FILE"
    echo "Error: Unstaged changes detected in the current branch. Please commit or stash your changes before running the pipeline."
    exit 1
fi

# Get the current branch \n----PIPELINE RUN AT 
CURRENT_BRANCH=$(git branch --show-current)

# Generate a unique branch name
BRANCH_NAME="pipeline-run-$(date +'%Y%m%d%H%M%S')"

echo "$(date +'%Y-%m-%d %H:%M:%S') - Starting pipeline run. Current branch: $CURRENT_BRANCH, New branch: $BRANCH_NAME" >> "$LOG_FILE"

# Create and switch to the new branch, setting its upstream to the current branch
git checkout -b "$BRANCH_NAME" --track "$CURRENT_BRANCH"

# Run the specified Python cleaning script
python "$PYTHON_SCRIPT" "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" true

# Check if the script succeeded
if [ $? -eq 0 ]; then
        if git diff --quiet "$CURRENT_BRANCH" "$BRANCH_NAME"; then
            # Log the absence of differences
            echo "$(date +'%Y-%m-%d %H:%M:%S') - No differences detected between $CURRENT_BRANCH and $BRANCH_NAME. No commit made." >> "$LOG_FILE"
            echo "Pipeline Run completed successfully"
            echo "No differences detected between $CURRENT_BRANCH and $BRANCH_NAME. No commit made."
            if $DEL_BRANCH then
                echo "Deleting $BRANCH_NAME"
                # Clean up the temporary branch
                git checkout "$CURRENT_BRANCH"
                git branch -D "$BRANCH_NAME"
            fi
            exit 0
        else
            # Update the log file locally
            echo "$(date +'%Y-%m-%d %H:%M:%S') - Pipeline run completed on branch $BRANCH_NAME" >> "$LOG_FILE"

            # Commit changes to the new branch
            git add "$DEST_DIR/."
            git commit -m "Pipeline run completed on $BRANCH_NAME"
            echo "Pipeline run completed. Changes committed to branch: $BRANCH_NAME"
        fi
else
    # Preserve the branch for debugging
    echo "Pipeline run failed. Changes remain in branch: $BRANCH_NAME"
    read -p "Do you want to delete this branch? (y/n): " user_input

    
    if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
        # Run the merge and cleanup script immediately
        git checkout $CURRENT_BRANCH
        git branch -D $BRANCH_NAME

    else   
        echo "Switch back to the original branch with 'git checkout $CURRENT_BRANCH' to continue work."
    fi
    exit 1
fi

# Output the branch for manual merge
echo "Changes have been committed to branch: $BRANCH_NAME"

# Output the branch for manual merge
echo "Changes have been committed to branch: $BRANCH_NAME"

if $RUN_EXTRA_COMMAND; then
    # Replace the following line with the command you want to run
    echo "Running optional command: Opening destination directory $DEST_DIR"
    xdg-open "$DEST_DIR" 2>/dev/null || open "$DEST_DIR" 2>/dev/null || echo "Could not open directory: $DEST_DIR"
fi

# Ask the user if they want to run the merge and cleanup immediately
read -p "Do you want to merge and clean up now? (y/n): " user_input

# Check if the user typed 'y'
if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
    # Run the merge and cleanup script immediately
    ./scripts/cleanup.sh "$BRANCH_NAME"
else
    # Print instructions for manual merge and cleanup
    echo "After reviewing changes, run 'scripts/cleanup.sh $BRANCH_NAME' to merge changes and delete the temporary branch."
fi