from typing import Callable, Optional
import json
import simplejson #type:ignore
import os
import networkx as nx #type:ignore
from networkx import DiGraph #type:ignore
from wordfreq import zipf_frequency
import math
import re
from collections import deque
import subprocess
import more_itertools as mit #type:ignore
import itertools as it
import logging
import time
from datetime import timedelta
from custom_logger import MyLogger,setup_logger
logger:MyLogger

LEVEL_2_CHARS:list[tuple[str,str]] = [
    ('e','C'),

    ('l','T'),
    ('l',"R"),
    ('l',"I"),
    ('t','L'),
    ('i','L'),
    
    
    ("ml","RM"),
    (r'v\b','Y'),
    (r'r\b','Y'),
    (r'z\b','Y'),
    ("ll","M"),
]
LEVEL_1_CHARS: list[tuple[str,str]] = [
    #no mess ups probably
    ("vv", "W"),
    ("sv",'W'),
    ('xv','w'),
    ("cl", "D"),
    ("cl",'A'),
    ("lll", "M"),
    ('ltl','M'),
    ("nl", "M"),
    ("ill","M"),
    ("rn","M"),

    ("ln", "M"),
    ('zn','M'),
    ('nz',"M"),
    ('ul',"M"),
    ("tn","M"),
    ('in',"M"),

    
    ('c','E'),
    ('lz','H'),
    ('lz','N'),
    ('la', 'N'),
    ('la', 'H'),

    ("il", "H"),
    ("ll", "H"),
    ("tl","H"),


    ("ll", "N"),
    ("rl", "N"),
    ("il", "N"),
    ("tl", "n"),
    
     ("tl", "U"),
    ("il", "U"),
     ("ll", "U"),
     ('ttl','M'),
     ('tll',"M"),
    #(r"s\b",""), # ones like these will remove any case of a pattern
]

THRESHOLDS = {
    4:3,
    3:5,
    2:5,
}
e=math.e

def get_unknown_words(unfixed_dir,pattern:re.Pattern,prelim_known:set[str],filter_func:Callable[[str],bool]|None=None)->tuple[set[str],set[str]]:
    
    def unknown_enough(word)->bool:
        return zipf_frequency(word,'en')<(math.e if len(word)>4 else 3) and len(word)<20
    filter_func =unknown_enough if filter_func is None else filter_func
    text_words:set[str] = set()

    for file in os.listdir(unfixed_dir):
        path = os.path.join(unfixed_dir,file)
        text = open(path).read()
        slightly_fixed1 = re.sub("1",'l',text)
        slightly_fixed = re.sub(r"[^\w\s]?","",slightly_fixed1)
        word_list:list[str] = [w.lower() for w in pattern.findall(slightly_fixed) if len(w)>=4]
        text_words.update(word_list)
    print(f"Known: {len(prelim_known)}")
    prelim_unknown = text_words.difference(prelim_known)
    print(f"Prelim unknown: {len(prelim_unknown)}")

    unknown_words = set([word.lower() for word in prelim_unknown if filter_func(word)])
    print("Filtered:",len(unknown_words))
    return unknown_words, text_words

def apply_t(s,old,new,i)->str:
    if i==-1:
        return re.sub(old,new,s)
    return s[:i] + new + s[i + len(old):] 
def known_enough(word:str)->tuple[bool,float]:
    zfreq = zipf_frequency(word,'en')
    return zfreq>THRESHOLDS.get(len(word),e), zfreq

def prune_graph(G: DiGraph, results: dict, next_char_queue: deque, new_words_for_next_iter: deque, logger):
    """
    Remove unnecessary nodes from the graph after each iteration.

    Parameters:
    - G (DiGraph): The graph to prune.
    - results (dict): Dictionary of confirmed corrections.
    - max_depth (int): Maximum depth level to keep nodes.
    - next_char_queue (deque): Nodes that are still being processed in the current iteration.
    - new_words_for_next_iter (deque): Nodes queued for the next iteration.
    - logger: Logger instance.
    """
    to_remove = set()
    queued_nodes = set(next_char_queue) | set(new_words_for_next_iter)  # Nodes still in process

    for node in list(G.nodes):
        node_data = G.nodes[node]
        root = node_data["root"]
        level = node_data.get("level", 0)
        # Remove nodes that are:
        # - Not in results
        # - Have no outgoing edges (dead ends)
        # - Are too deep in the graph
        # - Not in the queues for current or next iteration
        if node not in queued_nodes:
            if root in results and node not in results.values():
                if not list(G.successors(node)):  # No outgoing edges
                    to_remove.add(node)

    G.remove_nodes_from(to_remove)
    logger.notice("Pruned %d nodes after this iteration.", len(to_remove))


def clean_unconnected_nodes(G: DiGraph, results: dict, logger):
    """
    Remove nodes whose root is in results but are not connected to a valid correction.
    
    Parameters:
    - G (DiGraph): The directed graph.
    - results (dict): Dictionary of known corrections.
    - logger: Logger instance for logging actions.
    """
    valid_nodes = set(results.values())  # Nodes that lead to a valid correction
    to_remove = set()
    
    # Traverse the graph to mark reachable nodes from valid results
    for node in G.nodes():
        root = G.nodes[node]["root"]
        
        if root in results and node not in valid_nodes:
            # Check if the node connects to a valid correction
            reachable = any(final in valid_nodes for final in nx.descendants(G, node))
            
            if not reachable:
                to_remove.add(node)

    # Remove all unconnected nodes
    G.remove_nodes_from(to_remove)
    logger.notice("Removed %d unconnected nodes from the graph.", len(to_remove))

def run_cycle(unfixed_dir: str, chars: list[tuple[str, str]], known_corrections, max_iteration: int, logger,G:DiGraph):
    char_set = {char[0] for char in chars}  # Using set comprehension for efficiency
    pattern = re.compile("|".join(fr"\b[A-Za-z]*{re.escape(char)}[A-Za-z]*\b" for char in char_set))

    logger.info("Getting unknown words")
    prelim_known = set(known_corrections.keys())
    unknown_words, all_words = get_unknown_words(unfixed_dir, pattern, prelim_known)
    unknown_words.update(set(value for key,value in G.nodes.data('root',""))) #type:ignore
    unknown_words.discard("")

    logger.info("Initiating known words in graph")
    results = {}
    new_words_for_next_iter = deque(unknown_words)

    logger.info("Initiating graph")
    for word in unknown_words:
        G.add_node(word, root=word, final=None, level=0)

    current_iter = 0

    while current_iter < max_iteration:
        start_results = len(results)
        current_iter += 1
        logger.notice("Starting iteration %s", current_iter)

        results_gotten = deque()
        next_char_queue = new_words_for_next_iter
        new_words_for_next_iter = deque()

        for old, new in chars:
            logger.info("Processing character replacement: %s -> %s", old, new)
            char_queue = next_char_queue
            next_char_queue = deque()

            while char_queue:
                node_word = char_queue.popleft()  # Faster than .pop() for queue operations
                node_data = G.nodes[node_word]
                root = node_data["root"]

                if root in results:
                    continue

                node_solved = False
                indices = mit.locate(node_word, pred=lambda *x: mit.iequals(x, old), window_size=len(old)) if new else [-1]

                for i in indices:
                    new_word = apply_t(node_word, old, new, i).lower()

                    if new_word not in G:
                        known, zfreq = known_enough(new_word)
                        previously_corrected = known_corrections.get(new_word)

                        if previously_corrected:

                            logger.info("Previously corrected: '%s' -> '%s'", root, previously_corrected)
                            node_data["final"] = previously_corrected
                            G.add_node(new_word, root=root, final=previously_corrected)
                            results[root] = previously_corrected
                            node_solved = True
                        elif known:
                            results[root] = new_word
                            
                            node_data["final"] = new_word
                            G.add_node(new_word, root=root, final=new_word, freq=zfreq)
                            node_solved = True
                            logger.info("New valid word: '%s' (freq: %.2f)", new_word, zfreq)
                        else:
                            G.add_node(new_word, root=root, final=None, freq=zfreq)
                            new_words_for_next_iter.append(new_word)
                            logger.debug("Added to graph: %s", new_word)

                        G.add_edge(node_word, new_word, old=old, new=new, i=i)

                    else:
                        final = G.nodes[new_word].get("final")
                        if final:
                            results[root] = final
                            node_data["final"] = final
                            node_solved = True

                        elif not G.has_edge(node_word, new_word):
                            G.add_edge(node_word, new_word, old=old, new=new, i=i)

                    if node_solved:
                        break

                next_char_queue.append(node_word)

        logger.notice("%d results found in iteration %d, total %d", len(results) - start_results, current_iter, len(results))
        prune_graph(G,results,next_char_queue,new_words_for_next_iter,logger)

    still_out_there = set([x for x in unknown_words if x not in results])
    logger.info("Total results: %d", len(results))
    clean_unconnected_nodes(G,results,logger)
    return G, results, still_out_there


def git_commit(path, message: Optional[str] = None) -> None:
    """
    Commit changes from a specific file or directory in the repository to Git.

    Args:
        path (str): The file or directory containing the changes to commit.
        message (str): The commit message.
    """
    msg: str = message if message is not None else f"Modified {path}"
    try:
        if not os.path.exists(path):
            subprocess.run(["git", "rm", path], check=True)
        else:
            if os.path.isdir(path):
            # Stage changes in the specified directory
                subprocess.run(["git", "add", f"{path}/."], check=True)
            elif os.path.isfile(path):
                # Stage changes in the specified file
                subprocess.run(["git", "add", path], check=True)
            else:
                raise ValueError(f"The specified path '{path}' is neither a file nor a directory.")
            
            # Check if there are any staged changes
        subprocess.run(["git", "commit", "-m", msg], check=True)
        logging.info(f"Committed changes from {path} with message: '{msg}'")
    except Exception as e:
        logging.error("Error when committing: %s",e)
def main():
    home_dir = "networking/"
    log_file_path = "./networking.log"

    unfixed_dir = "manual_work/E2/problematic_unfixed"

    note = input("enter note for run: ")

    results1_file = "corrections1.json"
    results2_file= "currections2.json"

    results_all_file = "all_results.json"

    still_unknown_after_file = "still_out_there.txt"

    manual_corrections_path = 'manual_work/corrections.json'


    logger = setup_logger(log_file_path,note,overwrite=True)
    manual_corrections = json.load(open(manual_corrections_path,'r'))
    G=DiGraph()
    unknown_words, results1, still_out_there = run_cycle(unfixed_dir,LEVEL_1_CHARS,manual_corrections,5,logger,G)
    # with open("./unknown_words1.txt",'w') as f:
    #     f.writelines("\n".join(sorted(unknown_words)))
    results1_updated = {k:manual_corrections.get(v,v) for k,v in results1.items()}
    still_unknown_path = os.path.join(home_dir,still_unknown_after_file)
    with open(still_unknown_path,'w') as f:
            for l in still_out_there:
                if l in results1_updated:
                    logger.info("%s is not still out there, we got it",l)
                else:
                    f.write(f"{l}\n")
    known_corrections = {**manual_corrections,**results1_updated}


    save_path1 = os.path.join(home_dir,results1_file)
    with open(save_path1,'w') as file:
        file.write(simplejson.dumps(results1_updated,indent="\t",sort_keys=True))

    git_commit(home_dir,f"Part 1 of corecting: {note}")


    relevant_unknown,results2,still_still_out_there  = run_cycle(unfixed_dir,LEVEL_2_CHARS,known_corrections,4,logger,G)
    results2_updated = {k:known_corrections.get(v,v) for k,v in results2.items()}

    save2 = os.path.join(home_dir,results2_file)
    with open(save2,'w') as file:
        file.write(simplejson.dumps(results2_updated,indent="\t",sort_keys=True))
    all_results = {**results1_updated,**results2_updated}



    with open(still_unknown_path,'w') as f:
            for l in still_still_out_there:
                if l in all_results:
                    logger.info("%s is not still out there, we got it",l)
                else:
                    f.write(f"{l}\n")
    results_all_path = os.path.join(home_dir,results_all_file)
    with open(results_all_path,'w') as f:
        f.write(simplejson.dumps(all_results,item_sort_key=lambda item:item[1],indent="\t"))

    

if __name__=="__main__":
    # import sys
    # if len(sys.argv) != 2:
    #     print("Usage: python text_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>")
    #     sys.exit(1)

    # unfixed_dir = sys.argv[1]
    # save_path = sys.argv[2]

    main()