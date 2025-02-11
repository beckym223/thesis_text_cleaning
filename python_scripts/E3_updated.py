import os
import re
import logging
from utils import *
from text_cleaning import *
from constants import E3_FOOT_LINES

def handle_first_page(file:str, text:str)->str:
    disc,year,num,pagetxt = file.split("-")
    lines = text.split("\n")
    line_num = 0
    if int(year)<1912:
        num_lowercase_lines =0
        while num_lowercase_lines<2:
            line = lines[line_num]
            if re.search(r"[a-z]{3,}",line) is not None:
                num_lowercase_lines+=1
            else:
                num_lowercase_lines = 0
            line_num+=1
        start_line = line_num-1  
    else:
        while re.search(r"\b[a-z]+\b", lines[line_num]) is None:
            line_num+=1
        start_line = line_num+1
    return "\n".join(lines[start_line:])
def clean_headers_footers(dest_dir:str,commit_changes:bool):
    file:str
    try:
        for file in sorted(os.listdir(dest_dir)):
            try:
                if file[0]=='.':
                    continue
                disc,year,num,pagetxt = file.split("-")
                page=int(pagetxt[:-4])
                path = os.path.join(dest_dir,file)
                
                text = open(path,'r').read()
                
                text = jstor_and_stripping(text)
                if page>1:
                    lines = text.split("\n")
                    no_header = lines[1:]
                    text = "\n".join(no_header)
                else:
                    text = handle_first_page(file,text)
                with open(path,'w') as f:
                    f.write(text.strip())
            except Exception as e:
                logging.error(f"Error when processing file {file}")
    except Exception as e:
        logging.error(f"Error cleaning headers and footers: {e}")
        raise
    if commit_changes:
        git_commit(dest_dir,"Cleaned headers and footers")
    

def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,False)

    remove_files(dest_dir,is_first_page,commit_changes)

    # clean_headers_footers(dest_dir,commit_changes)

    # # remove_footnote_lines(dest_dir,E3_FOOT_LINES,commit_changes)

    # # fix_dash_errors_in_dir(dest_dir,commit_changes)
    
    # # handle_line_breaks_across_pages(dest_dir,commit_changes=True)

    # # split_into_paras_at_length(dest_dir,40,commit_changes)

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
