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
        for file in sorted(os.listdir(dir_path)):
            try:
                if file[0]=='.':
                    continue
                disc,year,num,pagetxt = file.split("-")
                page=int(pagetxt[:-4])
                path = os.path.join(dest_dir,file)
    
                text = open(path,'r').read()
                text = jstor_and_stripping(text)
                filtered_lines = [l for l in text.splitlines() if len(l)>3]
                if page!=1:
                    save_lines = filtered_lines[1:]
                    if (year=='1893' and page==15 or year=='1894' and page==21):
                        for i,line in enumerate(save_lines[::-1]):
                            line_num = (i+1) *-1
                            if re.search("[a-z]",line) is None:
                                save_lines = save_lines[:line_num]
                                break
                else:
                    line_num=0
                    any_upper =False
                    while True:
                        if len(re.findall(r'[a-z]',filtered_lines[line_num]))>2 and any_upper:
                            break
                        line_num+=1
                        any_upper=True
                    save_lines = filtered_lines[line_num:]

                text = "\n".join(save_lines)
                with open(path,'w') as f:
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
    
    handle_line_breaks_across_pages(dest_dir,commit_changes)

    split_into_paras_at_length(dest_dir,40,commit_changes)

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

