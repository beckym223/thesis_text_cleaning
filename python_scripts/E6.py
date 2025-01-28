import os
import re
import logging
from utils import *
from text_cleaning import *
from constants import E6_SPLIT_RANGES
import subprocess
from collections import defaultdict
def handle_first_page(file:str,text:str)->str:
    footnote_pattern= r"^(?:(?:[^\n]*\n)*?[^\n]*\b[A-Z]{2,}\b[^\n]*\n)(.+?)(?:[\n\*'A-Z]\s*Presidential|\s[t\*] *[A-Z]\w+.*$)"
    new_text = re.search(footnote_pattern,text,re.DOTALL)
    if new_text is not None:
        text= new_text.group(1)
    else:
        logging.warning(f"Cannot find footnote space for {file}")
    return text
    # w

def clean_headers_footers(dest_dir:str,commit_changes:bool):
    try:
        for file in sorted(os.listdir(dest_dir)):
            try:
                if file[0] =='.':
                    continue
                disc,year,num,pagetxt = file.rsplit("-")
                page=int(pagetxt[:-4])
                path = os.path.join(dest_dir, file)
                edge_case = year in ['2003','2004']
                text = open(path,'r').read()
                text = jstor_and_stripping(text)
                if edge_case:
                    start_line=None
                    end_line=None
                    lines = text.strip().split("\n")
                    line_num=0
                    while start_line is None:
                        if re.search(r"\b[A-Z]?[a-z]+\b",lines[line_num]) is None:
                            line_num+=1
                        else:
                            start_line=line_num
                    break_before_line = len(lines)-1
                    while end_line is None:
                        if re.search(r"[a-z]",lines[break_before_line-1]) is None:
                            break_before_line-=1
                        else:
                            end_line = break_before_line
                elif page<4 and re.search(r"\nBy[^\*\n]*?\b[A-Z]{2,}\b",text) is not None and not edge_case and year not in ['2006','2007']:
                    #handle first page

                    logging.info(f"Found first page {file}")
                    footnote_pattern= r"^(?:(?:[^\n]*\n)*?[^\n]*\b[A-Z]{2,}\b[^\n]*?\n)(.+?)(?:[\n\*'A-Z]\s*Presidential|\s[t\*] *[A-Z]\w+.*$)"
                    new_text = re.search(footnote_pattern,text,re.DOTALL)

                    if new_text is not None:
                        text= new_text.group(1)
                    else:
                        logging.warning(f"Cannot find footnote space for {file}")
                
                elif not edge_case:
                    text= "\n".join(text.splitlines()[1:])
                
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

def handle_covers_and_references(dest_dir:str,commit_changes:bool)->None:
    try:
        reference_first_pages:dict[str,int] = {}
        to_remove:dict[str,list[str]] =defaultdict(list)
        for file in sorted(os.listdir(dest_dir)):
            try:
                if file[0]==".":
                    continue

                new_text=None
                path = os.path.join(dest_dir,file)

                if "00.txt" in file:
                    logging.info(f"Setting {file} to remove")
                    to_remove['cover page'].append(path)
                    continue

                doc_id,pagetxt = file.rsplit("-",1)
                page=int(pagetxt[:-4])

                if reference_first_pages.get(doc_id,page)<page:
                    logging.info(f"Setting {file} to remove as reference page")

                    to_remove['reference page'].append(path)
                    continue

                text = open(path,'r').read()

                if page<4 and (len(text)<500 or file=="Economics-1983-0-01.txt"):
                    logging.info(f"Setting {file} author photo to remove")
                    to_remove['author photo page'].append(path)
                    continue

                if doc_id=="Economics-1970-0" and "APPENDIX" in text:
                        reference_first_pages[doc_id] = page
                        logging.info(f"Found appendix/reference page start for {doc_id} at page {page}")
                        new_text = text.split("APPENDIX")[0].strip()

                elif "REFERENCES" in text:
                    reference_first_pages[doc_id] = page
                    logging.info(f"Found reference page start for {doc_id} at page {page}")
                    new_text = text.split("REFERENCES")[0].strip()

                if new_text is not None:
                    with open(path,'w') as f:
                        f.write(new_text)
            except:
                logging.error(f"Error when figuring out file {file}")
                raise

        for reason,paths in to_remove.items():
            try:
                logging.info(f"Removing {len(paths)} {reason}s")
                if len(paths)==0:
                    logging.warning(f"No paths found with reason: {reason}")
                    continue
                for path in paths:
                    #logging.info(f"Removing {reason}: {os.path.basename(path)}")
                    os.remove(path)

                if commit_changes and len(paths)>0:
                    command = ["git", "rm","-q", *paths]
                    logging.info(f"Running removal command: '{' '.join(command)}'")
                    subprocess.run(command, check=True)
                    subprocess.run(["git",'commit',"-m",f"Removing {reason} files"])
            
            except Exception:
                logging.error(f"Error when removing files with reason {reason}")
                raise
        if commit_changes:
            git_commit(dest_dir,"Changed some reference pages")
    except Exception as e:
        logging.error(f"Error deleting files: {e}")
        raise
    logging.info("Successfully deleted")

def fix_extra_long_lines(dest_dir:str,commit_changes:bool):
    def correct(text:str)->str:
        return re.sub("  ","\n",text)
    apply_func_to_txt_dir(dest_dir,dest_dir,correct)
    if commit_changes:
        git_commit(dest_dir,"Turned big spaces into line breaks")
    


def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file,console_level=logging.INFO)

    initialize_directories(source_dir,dest_dir,commit_changes)

    handle_covers_and_references(dest_dir,commit_changes)
    
    clean_headers_footers(dest_dir,commit_changes)

    apply_splits_to_pages(dest_dir,E6_SPLIT_RANGES,commit_changes)

    fix_dash_errors_in_dir(dest_dir,commit_changes)

    fix_extra_long_lines(dest_dir,commit_changes)

    handle_line_breaks_across_pages(dest_dir,commit_changes)

    split_into_paras_at_length(dest_dir,25,commit_changes)



if __name__ == "__main__":
    import sys
    if len(sys.argv) != 5:
        print("Usage: python text_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>") #type:ignore
        sys.exit(1)

    source_dir = sys.argv[1]
    dest_dir = sys.argv[2]
    log_file = sys.argv[3]
    commit_changes = sys.argv[4].lower() == "true"

    main(source_dir, dest_dir, log_file, commit_changes)
