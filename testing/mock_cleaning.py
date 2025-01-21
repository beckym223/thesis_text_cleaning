import sys
import os
import time
import shutil
import logging
from ..python_scripts.utils import initialize_directories, git_commit, setup_logging
from ..python_scripts.text_cleaning import fix_dash_errors_in_dir,jstor_and_stripping

def clean_text(dest_dir:str,commit_changes:bool):
    file:str
    try:
        for file in sorted(os.listdir(dest_dir)):
            try:
                if file[0]=='.':
                    continue
                path = os.path.join(dest_dir,file)
                
                text = open(path,'r').read()
                
                text = jstor_and_stripping(text)
            except Exception as e:
                logging.error(f"Error when processing file {file}")
    except Exception as e:
        logging.error(f"Error cleaning headers and footers: {e}")
        raise
    if commit_changes:
        git_commit(dest_dir,"Cleaned text")


def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir, dest_dir, commit_changes)

    clean_text(dest_dir, commit_changes)

    fix_dash_errors_in_dir(dest_dir, commit_changes)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python mock_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>")
        sys.exit(1)

    source_dir = sys.argv[1]
    dest_dir = sys.argv[2]
    log_file = sys.argv[3]
    commit_changes = sys.argv[4].lower() == "true"

    main(source_dir, dest_dir, log_file, commit_changes)
