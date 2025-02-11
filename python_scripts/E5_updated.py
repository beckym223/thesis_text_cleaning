import os
import re
import logging
from utils import *
from text_cleaning import *
from constants import E5_SPLIT_RANGES
import subprocess

def remove_headers_normal_pages(text)->str:
    lines = text.splitlines()
    first_line=0
    while lowercase_words.search(lines[first_line]) is None:
        first_line+=1
    return "\n".join(lines[first_line:])


def clean_headers_footers(dest_dir:str,commit_changes:bool):
    global header_line
    header_line = re.compile(r"(\b[A-Z]+\b\s){2,}|^\d{1,2,4}|\d+\]^|\[[A-Z]+")
    global lowercase_words
    lowercase_words = re.compile(r"(\b[a-z]+\b\s?){2,}")
    try:
        for file in sorted(os.listdir(dest_dir)):
            path = os.path.join(dest_dir, file)
            text = open(path,'r').read()
            try:
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
                            text = text.split(footnote.group(0))[0]
                    elif len(text)<500:
                        os.remove(path)
                        if commit_changes:
                            logging.info(f"Staging {file} removal")
                            subprocess.run(["git", "rm", path], check=True)
                        continue
                    else:
                            text = remove_headers_normal_pages(text)
                else:
                    text = remove_headers_normal_pages(text)
            except IndexError:
                logging.warning(f"Cannot find start line for {file}")  
            except:
                logging.error(f"Exception when cleaning file {file}")
                raise    
            finally:
                with open(path,'w') as f:
                    f.write(text)
            
        if commit_changes:
            git_commit(dest_dir,"Cleaned headers and footers")
    except Exception as e:
        logging.error(f"Error when cleaning headers and footers: {e}")
        raise

def is_page_to_remove(file:str)->bool:
    return re.search(r"00.txt|1960-1|1953-0",file) is not None

def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,False)

    remove_files(dest_dir,is_page_to_remove,commit_changes)

    clean_headers_footers(dest_dir,commit_changes)

    # apply_splits_to_pages(dest_dir,E5_SPLIT_RANGES,commit_changes)

    # fix_dash_errors_in_dir(dest_dir,commit_changes)
    
    # handle_line_breaks_across_pages(dest_dir,commit_changes)

    # split_into_paras_at_length(dest_dir,50,commit_changes)

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
