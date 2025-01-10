import os
import shutil
import re
import itertools as it
import logging
from utils import *
from text_cleaning import *
from constants import E2_FOOT_LINES


def clean_text_files(dir_path: str,commit_changes:bool):
    """
    Cleans text files in the directory by removing unnecessary lines and whitespace.
    Specific rules are applied depending on the year and page number.
    """
    file = "none yet"
    try:
        files = sorted(os.listdir(dir_path))
        for file in files:
            try:
                if file.startswith('.'):
                    continue

                disc, year, num, page_txt = file.split("-")
                page = int(page_txt[:-4])
                path = os.path.join(dir_path, file)

                with open(path, 'r') as f:
                    text = f.read()

                text = text.split("This content downloaded from")[0].strip()
                lines = [line.strip() for line in text.split("\n")]

                if page != 1:
                    lines = lines[1:]
                    if len(lines[-1]) == 1 or (year == '1889' and page == 24):
                        logging.info(f"Deleting trailing line: '{lines[-1]}' in file: {file}")
                        lines = lines[:-1]
                elif year == '1888':
                    lines = lines[5:]
                else:
                    lines = lines[2:-3]

                text = "\n".join(lines).strip()

                with open(path, 'w') as f:
                    f.write(text)
            except Exception as e:
                logging.error(f"Error when processing file {file}")
        if commit_changes:
            git_commit(dir_path,"Basic processing and line removal")
    except Exception as e:
        logging.error(f"Error cleaning text files after file {file}: {e}")
        raise
def main(source_dir, dest_dir, log_file, commit_changes):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,commit_changes)

    remove_files(dest_dir,is_first_page,commit_changes)

    clean_text_files(dest_dir,commit_changes)

    fix_dash_errors_in_dir(dest_dir,commit_changes)

    remove_footnote_lines(dest_dir,E2_FOOT_LINES,commit_changes)
    
    handle_line_breaks_across_pages(dest_dir,commit_changes=True)

    # Run the cleaning steps


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 5:
        print("Usage: python text_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>")
        sys.exit(1)

    source_dir = sys.argv[1]
    dest_dir = sys.argv[2]
    log_file = sys.argv[3]
    commit_changes = sys.argv[4].lower() == "true"

    main(source_dir, dest_dir, log_file, commit_changes)

