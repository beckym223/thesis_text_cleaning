import os
import re
import logging
from utils import *
from text_cleaning import *
import subprocess
def handle_first_page(file:str,text:str)->str:
    footnote_pattern= r"^(?:(?:[^\n]*\n)*?[^\n]*\b[A-Z]{2,}\b[^\n]*\n)(.+?)(?:[\n\*'A-Z]\s*Presidential|\s[t\*] *[A-Z]\w+.*$)"
    new_text = re.search(footnote_pattern,text,re.DOTALL)
    if new_text is not None:
        text= new_text.group(1)
    else:
        logging.warning(f"Cannot find footnote space for {file}")
    return text
    # w

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
                
                text = open(path,'r').read()
                text = jstor_and_stripping(text)
                first_page = False
                if page<4:
                    if len(text)<500 or file=="Economics-1983-0-01.txt": #special case of first page
                        os.remove(path)
                        logging.info(f"Removing first page {file}{'- Staging for removal' if commit_changes else ''}")
                        if commit_changes:
                                subprocess.run(["git", "rm", path], check=True)
                        continue
                    if re.search(r"By[^\*]+\*?\n",text) is not None:
                        text = handle_first_page(file,text)
                        first_page=True
                if "REFERENCES" in text:
                    reference_first_pages[doc_id] = page
                    logging.info(f"Found reference page start for {doc_id} at page {page}")
                    text = text.split("REFERENCES")[0].strip()
                if doc_id=="Economics-1970-0" and "APPENDIX" in text:
                        reference_first_pages[doc_id] = page
                        logging.info(f"Found appendix/reference page start for {doc_id} at page {page}")
                        text = text.split("APPENDIX")[0].strip()

                text= "\n".join(text.splitlines()[1:]) if not first_page else text
                with open(path,'w') as f:
                    f.write(text.strip())
            except:
                logging.error(f"Exception when cleaning file {file}")
                raise
        if commit_changes:
            git_commit(dest_dir,"Cleaned headers and footers")
    except Exception as e:
        logging.error(f"Error when cleaning headers and footers: {e}")
        raise

def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,commit_changes)

    remove_files(dest_dir,is_first_page,commit_changes)

    clean_headers_footers_references(dest_dir,commit_changes)

    # apply_splits_to_pages(dest_dir,E7_SPLIT_RANGES,commit_changes)

    # fix_dash_errors_with_spaces_in_dir(dest_dir,commit_changes)

    # handle_quest_line_breaks(dest_dir,commit_changes)



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
