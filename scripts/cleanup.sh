#!/bin/bash

# Check if the correct number of arguments is provided
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <temporary_branch>"
    exit 1
fi

# Argument
TEMP_BRANCH="$1"

# Get the current branch (we assume the temporary branch is not the same as the current branch)
CURRENT_BRANCH=$(git branch --show-current)

# Get the upstream (parent) branch of the temporary branch
PARENT_BRANCH=$(git rev-parse --abbrev-ref "$TEMP_BRANCH@{u}" 2>/dev/null)

# If the upstream branch is not set, fall back to 'main' or 'master'
if [ -z "$PARENT_BRANCH" ]; then
    PARENT_BRANCH="main"
    echo "No upstream branch set for $TEMP_BRANCH, defaulting to '$PARENT_BRANCH'."
fi

# Checkout the parent branch
git checkout "$PARENT_BRANCH"

# Merge the changes from the temporary branch (fast-forward only)
git merge --ff-only "$TEMP_BRANCH"

# Check if the merge was successful
if [ $? -eq 0 ]; then
    echo "Merge successful. Changes have been merged from $TEMP_BRANCH to $PARENT_BRANCH."
    
    # Delete the temporary branch
    git branch -d "$TEMP_BRANCH"
    
    # Push the changes if required
    # git push origin "$PARENT_BRANCH"
else
    echo "Merge failed. The merge cannot be performed without a merge commit. Please resolve the situation."
    exit 1
fi
