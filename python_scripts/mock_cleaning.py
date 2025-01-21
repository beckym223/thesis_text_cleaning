import sys
import os
import logging
import shutil
from utils import initialize_directories, git_commit, setup_logging
from text_cleaning import fix_dash_errors_in_dir,jstor_and_stripping
from time import gmtime, strftime

def clean_text(dest_dir:str,commit_changes:bool,*args:list[str]):
    file:str
    files = sorted(os.listdir(dest_dir))
    last_file = len(files)-1
    try:
        for i,file in enumerate(files):
            try:
                if file[0]=='.':
                    continue
                path = os.path.join(dest_dir,file)
                
                text = open(path,'r').read()
                
                text = jstor_and_stripping(text)
                if "file-error" in args and i==last_file:
                    raise Exception(f"Something went wrong working with {file}")
            except Exception as e:
                logging.error(f"Error when processing file {file}")
                logging.warning("Error occured pre-commit")
    except Exception as e:
        logging.error(f"Error cleaning headers and footers: {e}")
        raise
    if commit_changes:
        if 'git-error' in args:
            logging.info("Making 'git-error' happen")
            git_commit("fake_dir","This shouldn't work")
        git_commit(dest_dir,"Cleaned text")

def change_text(dest_dir:str,commit_changes:bool):
    for file in sorted(os.listdir(dest_dir)):
        path = os.path.join(dest_dir,file)
        with open(path,'a') as f:
            f.write(f"\n Edited at: {strftime('%Y-%m-%d, %H:%M:%S',gmtime())}")
        logging.info(f"Edited {file} uniquely")
        if commit_changes:
            git_commit(path,f"Edited {file} uniquely")

def temp_creation(dest_dir:str,commit_changes:bool):
    if commit_changes:
        logging.info("Creating and committing temporary file")
        temp_path = os.path.join(dest_dir,'temp.txt')
        with open(temp_path,'w') as f:
            f.write("Hello world")
        git_commit(temp_path, "made temp file")
        logging.info("Removing temp file")
        os.remove(temp_path)
        git_commit(temp_path,'removed temp file')
    else:
        logging.warning("No temp changes to make or commit, will just go back")
    sys.exit(0)

def main(source_dir:str, dest_dir:str, log_file:str,commit_changes:bool,*args):
    setup_logging(log_file,console_level=logging.INFO)
    args = [x.split("--")[-1] for x in args]
    print("Args:", args)
    opt_args =["no-commit",'no-change','fail','git-error','file-error','success']
    for arg in args:
        if arg not in [*opt_args,source_dir,dest_dir,log_file,'true']:
            logging.warning(f"Unrecognized argument: {arg}, ignoring")
    if 'no-commit' in args:
        logging.info("Changing 'commit_changes' to false")
        commit_changes=False
 
    if not os.path.exists(dest_dir) or len(os.listdir(dest_dir))==0 and 'no-change' in args: 
        logging.info("Testing with no changes, but no files exist to change")
        temp_creation(dest_dir,commit_changes)
    temp_path = "./temp"
    try:

        initialize_directories(source_dir,dest_dir,commit_changes)
        if 'no-change' in args:
            temp_path = "./temp"
            shutil.copytree(dest_dir,temp_path)
        else:
            logging.info("Changing text uniquely")
            change_text(dest_dir,commit_changes)

        clean_text(dest_dir,commit_changes,*args)
        fix_dash_errors_in_dir(dest_dir,commit_changes)

    except:
        if os.path.exists(temp_path):
            logging.info("Deleting temp file")
            shutil.rmtree(temp_path)
        raise
    finally:
        if os.path.exists(temp_path):
            logging.info("Deleting temp file")
            shutil.rmtree(temp_path)
    
    if "fail" in args:
        logging.info("Running 'fail'")
        sys.exit(1)

    if "success" in args:
        logging.info("Seeming like a successful run")
        sys.exit(0)
    logging.info("Got to end of script, seems like it was a success")

if __name__ == "__main__":
    args = sys.argv
    if len(args) < 5:
        print("Usage: python mock_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>")
        sys.exit(1)
    print("Total args: ",len(args))
    source_dir = args[1]
    dest_dir = args[2]
    log_file = args[3]

    
    commit_changes = args[4].lower() == "true"
    main(source_dir, dest_dir, log_file,commit_changes,*args[5:])
