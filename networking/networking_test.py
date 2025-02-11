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
false_negatives = set(
    ['nearsightedness',]
)
TEST_WORDS = [
    "eurrielllllm",
    "meinbers",
    'ttlle',
    'wilich',
    'nearsiglltedness',
    'allleriean',
    'curriculllm',
]

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
                    logger.info("removing '%s'",node)
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
def test_cycle(unknown_words, chars: list[tuple[str, str]], known_corrections, max_iteration: int, logger, G:DiGraph):
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
        next_char_queue = new_words_for_next_iter
        new_words_for_next_iter = deque()

        for old, new in chars:
            logger.info("Processing character replacement: %s -> %s", old, new)
            char_queue = next_char_queue
            next_char_queue = deque()
            logger.info("In queue: %s",len(char_queue))
            while char_queue:
                node_word = char_queue.popleft()  # Faster than .pop() for queue operations
                node_data = G.nodes[node_word]
                root = node_data["root"]

                if root in results|known_corrections:
                    logger.info("'%s' with root '%s' already known as '%s', continuing",node_word,root,results.get(root,known_corrections.get(root)))
                    continue

                node_solved = False
                indices = mit.locate(node_word, pred=lambda *x: mit.iequals(x, old), window_size=len(old)) if new else [-1]

                for i in indices:
                    new_word = apply_t(node_word, old, new, i).lower()
                    logger.info("Created word '%s' from '%s'",new_word,node_word)

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
                            logger.info("Added to graph: %s", new_word)

                        logger.info("Creating edge between '%s' and '%s'",node_word,new_word)
                        G.add_edge(node_word, new_word, old=old, new=new, i=i)

                    else:
                        final = G.nodes[new_word].get("final")
                        if final:
                            logger.info("New word connected to final word, updating root result as '%s'-->'%s'",root,final)
                            results[root] = final
                            node_data["final"] = final
                            node_solved = True

                        elif not G.has_edge(node_word, new_word):
                            logger.info("Creating edge between '%s' and '%s'",node_word,new_word)
                            G.add_edge(node_word, new_word, old=old, new=new, i=i)

                    if node_solved:
                        break

                next_char_queue.append(node_word)

        logger.notice("%d results found in iteration %d, total %d", len(results) - start_results, current_iter, len(results))
        prune_graph(G,results,next_char_queue,new_words_for_next_iter,logger)
    still_out_there = [x for x in unknown_words if x not in results]
    print(still_out_there)
    logger.info("Total results: %d", len(results))
    clean_unconnected_nodes(G,results,logger)
    return results, still_out_there

def main():
    os.chdir("/Users/BeckyMarcusMacbook/Thesis/TextCleaning/")
    home_dir = "networking/test"
    os.makedirs(home_dir,exist_ok=True)
    log_file_path = "./networking/test/testing.log"

    unfixed_dir = "manual_work/E2/problematic_unfixed"

    manual_corrections_path = 'networking/results_FINAL.json'

    unknown_words = TEST_WORDS
    logger = setup_logger(log_file_path,"test run",overwrite=True)
    manual_corrections:dict = json.load(open(manual_corrections_path,'r'))
    for word in unknown_words:
        manual_corrections.pop(word,'')
    G=DiGraph()
    results1, still_out_there = test_cycle(unknown_words,LEVEL_1_CHARS,manual_corrections,5,logger,G)
    # with open("./unknown_words1.txt",'w') as f:
    #     f.writelines("\n".join(sorted(unknown_words)))
    results1_updated = {k:manual_corrections.get(v,v) for k,v in results1.items()}
    with open("networking/test/results1_test.json",'w') as f:
        f.write(simplejson.dumps(results1_updated,indent='\t'))
    logger.info("Still Unknown: %s",list(still_out_there))
    known_corrections = {**manual_corrections,**results1_updated}

    results2,still_still_out_there  = test_cycle(still_out_there,LEVEL_2_CHARS,known_corrections,4,logger,G)
    results2_updated = {k:known_corrections.get(v,v) for k,v in results2.items()}



    still_unknown_path = "networking/test/still_unknown.txt"
    with open(still_unknown_path,'w') as f:
            for l in still_still_out_there:
                    f.write(f"{l}\n")

    

if __name__=="__main__":
    # import sys
    # if len(sys.argv) != 2:
    #     print("Usage: python text_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>")
    #     sys.exit(1)

    # unfixed_dir = sys.argv[1]
    # save_path = sys.argv[2]
    main()