import os
import re
import logging
from utils import *
from text_cleaning import *
from constants import E7_TITLE_PAGE_BOUNDS,E7_SPLIT_RANGES
import subprocess


def clean_headers_footers_references(dest_dir:str,commit_changes:bool):
    try:
        reference_first_pages ={}
        for file in sorted(os.listdir(dest_dir)):
            try:
                if file[0] =='.':
                    continue
                doc_id,pagetxt = file.rsplit("-",1)
                page=int(pagetxt[:-4])
                path = os.path.join(dest_dir, file)
                if reference_first_pages.get(doc_id,page)<page: # means that it's after the reference first page
                    os.remove(path)
                    logging.info(f"Removing reference page {file}{'- Staging for removal' if commit_changes else ''}")
                    if commit_changes:
                            subprocess.run(["git", "rm", path], check=True)
                    continue

                title_pnum,start,stop = E7_TITLE_PAGE_BOUNDS[doc_id]
                if title_pnum>page:
                    os.remove(path)
                    logging.info(f"Removing cover page {file}{'- Staging for removal' if commit_changes else ''}")
                    if commit_changes:
                            subprocess.run(["git", "rm", path], check=True)
                    continue
                text = open(path,'r').read()
                text = jstor_and_stripping(text)
                if "REFERENCES" in text:
                    reference_first_pages[doc_id] = page
                    logging.info(f"Found reference page start for {doc_id} at page {page}")
                    text = text.split("REFERENCES")[0].strip()
                lines = text.splitlines()
                if title_pnum!=page:
                    stop = None
                    for i,line in enumerate(lines):
                        if re.search(r"\b[a-z]+\b",line) is not None:
                            start = i
                            break
                text = "\n".join(lines[start:stop])
                with open(path,'w') as f:
                    f.write(text)
            except:
                logging.error(f"Exception when cleaning file {file}")
                raise
        if commit_changes:
            git_commit(dest_dir,"Cleaned headers and footers")
    except Exception as e:
        logging.error(f"Error when cleaning headers and footers: {e}")
        raise

def handle_quest_line_breaks(dest_dir:str, commit_changes:bool):
    def remove_quest(text:str)->str:
        return re.sub(r"([a-zA-Z]+)\?\n([a-zA-Z]+)([^\w\n\s])?", # Captures 3 groups: first half of word, second half of word, optional punctuation
                      r"\1\2\3\n", #removes dash and moves line break
                      text)
    apply_func_to_txt_dir(dest_dir,dest_dir,remove_quest)
    if commit_changes:
        git_commit(dest_dir,"joined words split by ? across lines")


def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,commit_changes)

    clean_headers_footers_references(dest_dir,commit_changes)

    apply_splits_to_pages(dest_dir,E7_SPLIT_RANGES,commit_changes)

    fix_dash_errors_in_dir(dest_dir,commit_changes)

    handle_quest_line_breaks(dest_dir,commit_changes)



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
