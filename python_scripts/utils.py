import os
import subprocess
import logging
from typing import Optional, Any, Callable,Concatenate
import shutil
import functools

def commit(_func:Optional[Callable]=None,
           to_commit_default = False,
           to_commit_arg:int|str=-1,
           commit_msg:Optional[str]=None,
           commit_path_arg:int|str="dir_path",
           default_path:str = "./",
           *args:list, **kwargs:dict[str,Any]):
    def decorator_commit(func:Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cm = kwargs.get("commit_msg",commit_msg)
            to_commit = (args[to_commit_arg] 
                                  if isinstance(to_commit_arg,int) 
                                  else kwargs.get(to_commit_arg,to_commit_default))
            result = func(*args, **kwargs)

            if to_commit:
                path_to_commit = (args[commit_path_arg] 
                                  if isinstance(commit_path_arg,int) 
                                  else kwargs.get(commit_path_arg,default_path))
                git_commit(path_to_commit,cm)
                return result
            else:
                print("Nothing to commit")
        return wrapper
            

    if _func is None:
        return decorator_commit
    else:
        return decorator_commit(_func)
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

@commit(commit_msg="Initializing directories")
def initialize_directories(source_dir: str, dest_dir: str,commit_changes:bool):
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


    
def apply_func_to_txt_dir(source_dir:str,
                          dest_dir:str,
                          func:Callable[Concatenate[str,...],str],
                          skip_if_exists=False,
                          pass_filename=False,
                          *args, **kwargs):
    """
    Applies a given function to the contents of all .txt files in a directory tree and writes the 
    results to a new directory structure, maintaining the same relative folder structure.

    Parameters:
    -----------
    start_dir_path : str
        The root directory containing subdirectories and .txt files to process.
    write_to : str
        The root directory where the processed .txt files will be written.
    func : function
        The function to apply to the contents of each .txt file. It should take the file's text 
        content as its first argument and return the modified content.
    skip_if_exists : bool, optional
        If True, the function will skip files that already exist in the write_to directory.
        Defaults to False.
    pass_filename : bool, optional
        If True, the filename will also be passed to the function along with the file content.
        Defaults to False.
    *args : tuple
        Additional positional arguments to pass to the `func`.
    **kwargs : dict
        Additional keyword arguments to pass to the `func`.

    Returns:
    --------
    None
    """
    for file_name in sorted(os.listdir(source_dir)):
        if file_name[0] ==".":
            continue
        src_path = os.path.join(source_dir,file_name)
        new_file_path = os.path.join(dest_dir,file_name)
   
        if os.path.exists(new_file_path) and skip_if_exists:
            continue
        
        # Open the original file and read its content
        with open(src_path, 'r') as f:
            old_text = f.read()
            
        # Apply the provided function to the text content (with or without filename)
        if pass_filename:
            new_text = func(old_text, file_name, *args, **kwargs)  # Pass file name
        else:
            new_text = func(old_text, *args, **kwargs)  # Only pass text content
        
    # Write the modified text to the new file path
        with open(new_file_path, 'w') as f:
            f.write(new_text)


