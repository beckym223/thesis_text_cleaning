import logging
import os
import re
from collections import deque

from constants import E5_SPLIT_RANGES
from more_itertools import collapse, split_after, unzip
from text_cleaning import (fix_dash_errors_in_dir,
                           fix_line_breaks_across_footnote_pages,
                           jstor_and_stripping, remove_files,
                           split_into_paras_at_length)
from utils import *


def remove_headers_normal_pages(text,file)->str:
    try:
        lines = text.splitlines()
        first_line=0
        while lowercase_words.search(lines[first_line]) is None:
            first_line+=1
        return "\n".join(lines[first_line:])
    except IndexError:
        logging.warning(f"Cannot find starting text for {file}")
        return text


def clean_headers_footers(dest_dir:str,fn_split,commit_changes:bool):
    global header_line
    header_line = re.compile(r"(\b[A-Z]+\b\s){2,}|^\d{1,2,4}|\d+\]^|\[[A-Z]+")
    global lowercase_words
    lowercase_words = re.compile(r"(\b[a-z]+\b\s?){2,}|TABLE|CHART|FIGURE")
    try:
        for file in sorted(os.listdir(dest_dir)):
            path = os.path.join(dest_dir, file)
            text = open(path,'r').read()
            if file[0] =='.':
                continue
            disc,year,num,pagetxt = file.split("-")
            page=int(pagetxt[:-4])
            text = jstor_and_stripping(text)
            if "REFERENCES" in text:
                print(f"Reference at {file}")
                logging.info(f"Found reference start in {file}")
            if page<4:
                author_line =re.search("\n(By [^\n]+\n)",text)
                if author_line is not None:
                    text = text.split(author_line.group(1),1)[1]
                    footnote = re.search(r"\n[\*'\d]+\s*[Pp]resident",text)
                    if footnote is None:
                        logging.warning(f"Cannot find footnote for {file}")
                    else:
                        m:str = footnote.group(0)
                        before, after = text.rsplit(m,1)
                        text = before+fn_split+m+after
                elif len(text)<500:
                    os.remove(path)
                    continue
                else:
                        text = remove_headers_normal_pages(text,file)
            else:
                text = remove_headers_normal_pages(text,file)
 
            with open(path,'w') as f:
                    f.write(text)
            
        if commit_changes:
            git_commit(dest_dir,"Cleaned headers and footers")
    except Exception as e:
        logging.error(f"Error when cleaning headers and footers: {e}")
        raise

def apply_splits_to_pages(dir_name:str,split_dict:dict[str,list[tuple[int,int]]],commit_changes:bool,split_join="\n"):
    for file,splits in split_dict.items():
        try:
            indices = deque(collapse(sorted(splits,key=lambda x: x[0])))
            if indices[0]==0:
                indices.popleft()
            def pred(i):
                if not indices:
                    return False
                if i[0]>=indices[0] and i[1]=="\n":
                    indices.pop()
                    return True
                return False
            path = os.path.join(dir_name,file)
            text = open(path).read().strip()
            text = split_join.join([f for f in map(lambda x: "".join(unzip(x)[1]),split_after(enumerate(text),pred),) if f.strip()]) #type:ignore
            with open(path,'w') as f:
                f.write(text)
        except FileNotFoundError:
            logging.warning(f"File {file} not found in directory {dir_name}. Continuing.")
            continue
        except Exception as e:
            logging.error(f"Error with text splitting of {file}")
            raise
    if commit_changes:
        git_commit(dest_dir,"found a thing")

def is_page_to_remove(file:str)->bool:
    return re.search(r"00.txt|1960-1|1953-0",file) is not None

def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    fn_split = "\n\n#### Split:\n"
    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,commit_changes)

    remove_files(dest_dir,is_page_to_remove,commit_changes)

    clean_headers_footers(dest_dir,fn_split,commit_changes)

    apply_splits_to_pages(dest_dir,E5_SPLIT_RANGES,commit_changes,split_join = fn_split)

    fix_dash_errors_in_dir(dest_dir,commit_changes)
    
    fix_line_breaks_across_footnote_pages(dest_dir,commit_changes,fn_split)

    split_into_paras_at_length(dest_dir,50,commit_changes)

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
