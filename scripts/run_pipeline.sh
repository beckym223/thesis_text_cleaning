#!/bin/bash
RUN_EXTRA_COMMAND=false
DEL_BRANCH=true
BRANCH_NAME="pipeline-run-$(date +'%Y%m%d%H%M%S')"
VERBOSE=false

# Process short options
while getopts "okvb:" opt; do
    case "$opt" in 
        o)
            RUN_EXTRA_COMMAND=true
            ;;
        k)
            DEL_BRANCH=false
            ;;
       b)
            if [ -n "$OPTARG" ]; then
                echo "BRANCH NAME found: '$OPTARG'"

                BRANCH_NAME=$OPTARG
            else
                echo "Error: Missing branch name for -b option."
                exit 1
            fi
            
            ;;
        v)
            VERBOSE=true
            ;;
        *)
            echo "Usage: $0 [-o|--open] [-k|--keep] [-b|--branch] <source_dir> <dest_dir> <log_file> <python_script> [extra_args...]"
            exit 1
            ;;
    esac
done
if $VERBOSE; then
echo "Arguments recieved: $*@"
fi
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
        --branch)
            shift
            BRANCH_NAME="$1"
            ;;
                --help)
            echo "Usage: $0 [-o|--open] [-k|--keep] [-b|--branch] <source_dir> <dest_dir> <log_file> <python_script> [extra_args...]"
            exit 0
            ;;
        *)
            break
            ;;
    esac
    shift
done

# if [ "$#" -le 3 ]; then
#     echo "Wrong number of args $#: Usage: $0 [-o|--open] [-k|--keep] [-b|--branch] <source_dir> <dest_dir> <log_file> <python_script> [extra_args...]"
#     exit 1
# fi

# Arguments
SOURCE_DIR="$1"
DEST_DIR="$2"
LOG_FILE="$3"
PYTHON_SCRIPT="$4"
echo "DEBUG: BRANCH_NAME = '$BRANCH_NAME'"

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


echo "$(date +'%Y-%m-%d %H:%M:%S') - INFO - Starting pipeline run. Current branch: $CURRENT_BRANCH, New branch: $BRANCH_NAME" >> "$LOG_FILE"

# Create and switch to the new branch, setting its upstream to the current branch
git checkout -b "$BRANCH_NAME" --track "$CURRENT_BRANCH"

# Run the specified Python cleaning script
python "$PYTHON_SCRIPT" "$SOURCE_DIR" "$DEST_DIR" "$LOG_FILE" true "$@"

# Check if the script succeeded
# shellcheck disable=SC2181
if [ $? -eq 0 ]; then #ignore
        if git diff --quiet "$CURRENT_BRANCH" "$BRANCH_NAME"; then
            # Log the absence of differences
            echo "$(date +'%Y-%m-%d %H:%M:%S') - INFO - No differences detected between $CURRENT_BRANCH and $BRANCH_NAME. No commit made." >> "$LOG_FILE"
            echo "Pipeline Run completed successfully"
            echo "No differences detected between $CURRENT_BRANCH and $BRANCH_NAME. No commit made."
            if $DEL_BRANCH; then
                echo "Deleting $BRANCH_NAME"
                # Clean up the temporary branch
                git checkout "$CURRENT_BRANCH"
                git branch -D "$BRANCH_NAME"
            else
                echo "Keeping $BRANCH_NAME."
                echo "To delete, run 'git checkout $CURRENT_BRANCH' and git branch -d $BRANCH_NAME"
            fi
            exit 0
        else
            # Update the log file locally
            echo "$(date +'%Y-%m-%d %H:%M:%S') - INFO - Pipeline run completed on branch $BRANCH_NAME" >> "$LOG_FILE"

            # Commit changes to the new branch
            git add "$DEST_DIR/."
            git commit -m "Pipeline run completed on $BRANCH_NAME"
            echo "Pipeline run completed. Changes committed to branch: $BRANCH_NAME"
        fi
else # if the pipeline run fails

    # Preserve the branch for debugging
    echo "Pipeline run failed. Changes remain in branch: $BRANCH_NAME"

    # If any changes remain
    if [ -n "$(git status --porcelain)" ]; then
        echo "$(date +'%Y-%m-%d %H:%M:%S') - WARNING - Outstanding changes from failed pipeline run" >> "$LOG_FILE"
        
        # shellcheck disable=SC2162
        read  -p "Some changes are uncommited in branch. Do you want to commit them? (y/n)" user_input
        if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
            echo "$(date +'%Y-%m-%d %H:%M:%S') - INFO - Committing outstanding changes from failed pipeline run" >> "$LOG_FILE"
            echo "Staging and committing all changes"
            git commit -a "Committing outstanding changes from failed pipeline run"
        fi
    fi

    # shellcheck disable=SC2162
    read -p "Do you want to delete this branch? (y/n): " user_input
    if [[ "$user_input" == "y" || "$user_input" == "Y" ]]; then
        # Run the merge and cleanup script immediately
        git checkout "$CURRENT_BRANCH"
        git branch -D "$BRANCH_NAME"
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

