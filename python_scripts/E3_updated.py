import logging
import os
import re

import numpy as np
from constants import E3_FOOT_PAGES, FOOTNOTE_SEPARATER
from text_cleaning import (fix_dash_errors_in_dir,
                           fix_line_breaks_across_footnote_pages,
                           is_first_page, jstor_and_stripping, remove_files,
                           split_into_paras_at_length)
from utils import git_commit, initialize_directories, setup_logging


def handle_first_page(file:str, text:str)->str:
    disc,year,num,pagetxt = file.split("-")
    lines = text.split("\n")
    line_num = -1
    if int(year)<1912:
        num_lowercase_lines =0
        while num_lowercase_lines<2:
            line_num+=1
            line = lines[line_num]
            if re.search(r"[a-z]{3,}",line) is not None:
                num_lowercase_lines+=1
            else:
                num_lowercase_lines = 0
            
        start_line = line_num-1  
        
    else:
        while re.search(r"\b[a-z]+\b", lines[line_num]) is None:
            line_num+=1
        start_line = line_num+1
    logging.info(f"Found start line for {file} at line {start_line}")
    return "\n".join(lines[start_line:])
def clean_headers_footers(dest_dir:str,commit_changes:bool):
    file:str
    line_num = re.compile(r"\n(\d{1,3}\n*)$")
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
                    no_header = lines[2:]
                    text = "\n".join(no_header)
                else:
                    text = handle_first_page(file,text)
                if file=="Economics-1907-0-05.txt":
                    lines= text.splitlines()
                    to_change = np.array(lines[:10])
                    order =  [3,4,5,6,7,0,8,1,9,2]
                    text = "\n".join(["\n".join(to_change[order]),*lines[10:]])
                text = line_num.sub("",text,1)
                with open(path,'w') as f:
                    f.write(text.strip())
            except Exception as e:
                logging.error(f"Error when processing file {file}")
    except Exception as e:
        logging.error(f"Error cleaning headers and footers: {e}")
        raise
    if commit_changes:
        git_commit(dest_dir,"Cleaned headers and footers")
    
def find_footnote_lines(dest_dir,split_str,commit_changes):
    for file in E3_FOOT_PAGES:
        path = os.path.join(dest_dir,file)
        with open(path,'r') as f:
            text = f.read()
        lines = text.splitlines()
        start_options = [r'¹', r'\*', r'[A-Z]([a-z]+|\.) [A-Z]\.', r"'", r'\d{1,2}(?!\d)', r'System of']

        p = re.compile(fr"^\s?(?P<line_start>{'|'.join(start_options)})(?P<rest>.*)$")
        fn_start = None
        i = -1
        since_last=0
        while i>=-10 or since_last<5:
            line = lines[i]
            m = p.match(line)
            if m:
                since_last=0
                fn_start = i
                symbol =m.group('line_start')
                lines[i] = f"{re.escape(symbol) if symbol=="*" else symbol}{m.group('rest')}"
                
            else:
                since_last+=1
            i-=1

        if fn_start is not None:
            with open(path,'w') as f:
                f.write('\n'.join(lines[:fn_start])+f"{split_str}{'\n'.join(l for l in lines[fn_start:] if l).strip()}")
        else:
            logging.warning(f"Could not find footnote for {path}")

    if commit_changes:
        git_commit(dest_dir,"separated footnote lines")


def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):
    fn_sep = FOOTNOTE_SEPARATER
    
    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,False)

    remove_files(dest_dir,is_first_page,commit_changes)

    clean_headers_footers(dest_dir,commit_changes)

    find_footnote_lines(dest_dir,fn_sep,commit_changes)

    fix_dash_errors_in_dir(dest_dir,commit_changes)
    
    fix_line_breaks_across_footnote_pages(dest_dir,commit_changes=True,split_before=fn_sep)

    split_into_paras_at_length(dest_dir,40,commit_changes)

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
