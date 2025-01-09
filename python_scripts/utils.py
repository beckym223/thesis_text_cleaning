import os
import subprocess
import logging
from typing import Optional, Any, Callable
import shutil
import functools


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logging.info("Logging initialized.")

def initialize_directories(source_dir: str, dest_dir: str):
    """
    Copies the contents of the source directory to the destination directory.
    Deletes the destination directory first if it already exists.
    """
    try:
        if os.path.exists(dest_dir):
            logging.info(f"Removing existing directory: {dest_dir}")
            shutil.rmtree(dest_dir)
        logging.info(f"Copying contents from {source_dir} to {dest_dir}")
        shutil.copytree(source_dir, dest_dir)
    except Exception as e:
        logging.error(f"Failed to initialize directories: {e}")
        raise


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

def commit(_func:Optional[Callable]=None,
           commit_default = False,
           commit_msg=None,
           commit_path_arg:Optional[int|str]="dir_path",
           default_path:str = "./",
           *args:list, **kwargs:dict[str,Any]):
    def decorator_commit(func:Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cm = kwargs.get("commit_msg",commit_msg)
            to_commit = kwargs.get("commit_changes",commit_default)
            result = func(*args, **kwargs)

            if to_commit:
                path_to_commit = (args[commit_path_arg] 
                                  if isinstance(commit_path_arg,int) 
                                  else kwargs.get(commit_path_arg,default_path)) #type:ignore
                git_commit(path_to_commit,cm)
                return result
            else:
                print("Nothing to commit")
        return wrapper
            

    if _func is None:
        return decorator_commit
    else:
        return decorator_commit(_func)


