import os
import re
import logging
from utils import *
from text_cleaning import *
from constants import E4_ABSTRACT_DICT, E4_FOOT_LINES

def handle_first_pages(file:str,text:str)->str:
    return ""

def clean_headers_and_footers(dest_dir:str,commit_changes:bool):
    for file in sorted(os.listdir(dest_dir)):
        disc,year,num,pagetxt = file.split("-")
        page=int(pagetxt[:-4])
        path = os.path.join(dest_dir, file)
        pages_to_delete = []
        text = open(path,'r').read()
        text = jstor_and_stripping(text)
        if page<4:
            author_line =re.search("\n(By .*\n)",text)
            if author_line is not None:
                text = text.split(author_line.group(1),1)[1]
                footnote = re.search(r"\n[\*'\d]+\s*[Pp]resident",text)
                if footnote is None:
                    logging.warning(f"Cannot find footnote for {file}")
                else:
                    text = text.split(footnote.group(0))[0]
            elif len(text)<500:
                pages_to_delete.append(path)
                continue
            else:
                text = text.strip().split("\n",1)[1]
        else:
            text = text.strip().split("\n",1)[1]
        with open(path,'w') as f:
            f.write(text)

def is_page_to_remove(file:str)->bool:
    return re.search(r"00.txt|1960-1|1953-0",file) is not None

def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,commit_changes)

    remove_files(dest_dir,is_page_to_remove,commit_changes)

    # clean_headers_footers(dest_dir,commit_changes)

    # handle_last_page_authors(dest_dir,commit_changes)

    remove_footnote_lines(dest_dir,E4_FOOT_LINES,commit_changes)

    fix_dash_errors_in_dir(dest_dir,commit_changes)
    
    handle_line_breaks_across_pages(dest_dir,commit_changes=True)

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
