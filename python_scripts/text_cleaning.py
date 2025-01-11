import os
import logging
import re
import itertools as it
from collections.abc import Callable
from utils import commit, apply_func_to_txt_dir

@commit(commit_msg="Removed files")
def remove_files(dir_path: str,
                 decision_function:Callable[[str],bool],
                 commit_changes:bool,
                  ):
    """
    Removes files with page 0 from the directory.
    """
    try:
        files = sorted(os.listdir(dir_path))
        for file in files:
            try:
                if decision_function(file):
                    os.remove(os.path.join(dir_path, file))
                    logging.info(f"Removed file: {file}")
            except ValueError:
                logging.warning(f"Skipping file with unexpected format: {file}")
        if commit_changes:
            logging.info("Committing changes")
    except Exception as e:
        logging.error(f"Error removing first-page files: {e}")
        raise

@commit(commit_msg='Handled line breaks between pages')
def handle_line_breaks_across_pages(dir_path: str,commit_changes:bool):
    """
    Fixes line breaks across pages by merging broken words from consecutive files.
    """
    try:
        files = sorted(os.listdir(dir_path))
        for first, second in it.pairwise(files):
            try:
                if first.split("-")[:3] != second.split("-")[:3]:
                    continue

                path1 = os.path.join(dir_path, first)
                path2 = os.path.join(dir_path, second)

                with open(path1, 'r') as f1, open(path2, 'r') as f2:
                    text1 = f1.read()
                    text2 = f2.read()

                if text1.endswith("-"):
                    first_word = re.match(r"^\S+", text2).group() #type:ignore
                    new_text2 = re.sub(r"^\S+\s", "", text2)
                    new_text1 = text1[:-1] + first_word

                    with open(path1, 'w') as f1, open(path2, 'w') as f2:
                        f1.write(new_text1.strip())
                        f2.write(new_text2.strip())

                    logging.info(f"Merged line break between {first} and {second}")

            except Exception as e:
                logging.warning(f"Error handling line break between {first} and {second}: {e}")
    except Exception as e:
        logging.error(f"Error handling line breaks: {e}")
        raise

def fix_dash_errors(text:str)->str:
    new_text = re.sub(r"([a-zA-Z]+)-\n([a-zA-Z]+)([^\w\n\s])?", # Captures 3 groups: first half of word, second half of word, optional punctuation
                      r"\1\2\3\n", #removes dash and moves line break
                      text)
    new_text_lines_stripped=[line.strip() for line in new_text.split('\n')] #remove any extra leading or trailing whitespace
    return "\n".join(new_text_lines_stripped).strip() #join lines back together

@commit(commit_msg="Fixed dash errors between lines")
def fix_dash_errors_in_dir(dir_path,commit_changes):
    try:
        apply_func_to_txt_dir(dir_path,dir_path,fix_dash_errors)
    except Exception as e:
        logging.error(f"Exception while fixing dash errors: {e}")


def jstor_and_stripping(text:str)->str:
    lines = text.split("\n")
    lines_stripped = [l.strip() for l in lines]
    text = "\n".join(lines_stripped)
    
    jstor_split = text.split("This content downloaded from")
    return jstor_split[0]

def is_first_page(filename:str)->bool:
    return "00.txt" in filename

@commit(commit_msg="Removed footnote lines")
def remove_footnote_lines(dir_path:str,foot_dict:dict[str,int],commit_changes:bool):
    for file, first_foot_line in foot_dict.items():
        try:
            path = os.path.join(dir_path,file)
            text = open(path,'r').read()
            kept_lines = text.splitlines()[:first_foot_line]
            with open(path,'w') as f:
                f.write("\n".join(kept_lines).strip())
        except Exception as e:
            logging.error(f"Exception when removing footnote lines with file {file}: {e}")

def split_text(text:str,splits:list[tuple[int,int]])->str:
    old_text=text
    for start,end in splits:
        text = text.replace(old_text[start:end],"")
    return text


@commit(commit_msg = "Sliced texts on predetermined indices")
def apply_splits_to_pages(dir_name:str,split_dict:dict[str,list[tuple[int,int]]],commit_changes:bool):
    for file,splits in split_dict.items():
        try:
            path = os.path.join(dir_name,file)
            text = open(path).read().strip()
            text = split_text(text,splits)
            with open(path,'w') as f:
                f.write(text)
        except FileNotFoundError:
            logging.warning(f"File {file} not found in directory {dir_name}. Continuing.")
            continue
        except Exception as e:
            logging.error(f"Error with text splitting of {file}")
            raise

