import os
import subprocess
import logging
from typing import Optional

def git_commit(path: str, message: Optional[str] = None) -> None:
    """
    Commit changes from a specific file or directory in the repository to Git.

    Args:
        path (str): The file or directory containing the changes to commit.
        message (str): The commit message.
    """
    msg: str = message if message is not None else f"Modified {path}"
    try:
        if not os.path.exists(path):
            subprocess.run(["git", "rm", path], check=True)
        else:
            if os.path.isdir(path):
            # Stage changes in the specified directory
                subprocess.run(["git", "add", f"{path}/."], check=True)
            elif os.path.isfile(path):
                # Stage changes in the specified file
                subprocess.run(["git", "add", path], check=True)
            else:
                raise ValueError(f"The specified path '{path}' is neither a file nor a directory.")
            
            # Check if there are any staged changes
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            check=False,
            capture_output=True
        )
        
        if result.returncode == 1:  # Changes are staged
            subprocess.run(["git", "commit", "-m", msg], check=True)
            logging.info(f"Committed changes from {path} with message: '{msg}'")
        else:
            logging.info(f"No changes to commit in path: {path}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Git operation failed: {e}")
        raise
    except ValueError as e:
        logging.error(str(e))
        raise
