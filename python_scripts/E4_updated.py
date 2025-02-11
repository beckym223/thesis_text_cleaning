import os
import re
import logging
from utils import *
from text_cleaning import *
from constants import E4_ABSTRACT_DICT, E4_FOOT_LINES

def handle_first_page(file:str, text:str)->str:
    lines = text.split("\n")
    save_path = os.path.join(dest_dir,file)
    after_abstract = E4_ABSTRACT_DICT.get(file)
    if after_abstract is not None:
        for i,line in enumerate(lines):
            if line.startswith(after_abstract):
                lines = lines[i:]
                break
        #→find the line that starts with that text
        #delete everything before it
    else:
        all_caps_line=0
        #finding first all caps line
        while re.search('[a-z]',lines[all_caps_line]) is not None:
            all_caps_line+=1
        #finding line with not all caps
        first_real_line = all_caps_line+1
        while re.search(r"[a-z]", lines[first_real_line]) is None:
            first_real_line+=1
        if re.search("Presidential [aA]ddress",lines[first_real_line]) is not None:
            first_real_line+=2
            if "1933-0" in file or "1934-0" in file:
                first_real_line+=1
            stop_line = None
        else: #means presidential address in footnote
            stop_line = first_real_line
            try:
                while "Presidential address" not in lines[stop_line]:
                    stop_line+=1
            except:
                print(f"Presidential address not found in footnote for {file}")
                with open(save_path,'w') as f:
                    f.write("\n".join(lines))
        lines = lines[first_real_line:stop_line]
    return "\n".join(lines)

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
                    no_header = lines[3:]
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

def is_page_to_remove(file:str)->bool:
    disc,year,num,pagetxt = file.split("-")
    page=int(pagetxt[:-4])
    return page==0 or ('1933-1' in file and page>=9)
    
def handle_last_page_authors(dest_dir:str,commit_changes:bool):
    try:
        last_pages:list[str] = []
        files = sorted(os.listdir(dest_dir))
        for i,file in enumerate(files):
            if '01' in file and i!=0:
                last_pages.append(files[i-1])
        for page in last_pages:
            try:
                path = os.path.join(dest_dir,page)
                text = open(path,'r').read()
                lines = text.split("\n")
                for line in lines[::-1]:
                    found = re.search(r"[A-Z\.\s]{5,}",line)
                    if found is not None:
                        new_page = text.rsplit(found.string,1)[0].strip()
                        with open(path,'w') as f:
                            f.write(new_page)
            except:
                logging.error(f"Error finding author in file {last_pages}")
        if commit_changes:
            git_commit(dest_dir, "Removed author name on last page")
    except Exception as e:
        logging.error(f"Exception when removing last page authors: {e}")
def main(source_dir:str, dest_dir:str, log_file:str, commit_changes:bool):

    setup_logging(log_file)

    initialize_directories(source_dir,dest_dir,False)

    remove_files(dest_dir,is_page_to_remove,commit_changes)

    clean_headers_footers(dest_dir,commit_changes)

    handle_last_page_authors(dest_dir,commit_changes)

    remove_footnote_lines(dest_dir,E4_FOOT_LINES,commit_changes)

    fix_dash_errors_in_dir(dest_dir,commit_changes)
    
    handle_line_breaks_across_pages(dest_dir,commit_changes=True)

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
