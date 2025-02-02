from typing import Callable, Optional
import json
import simplejson #type:ignore
import os
import networkx as nx #type:ignore
from networkx import DiGraph #type:ignore
from wordfreq import zipf_frequency
import math
import re
from collections import deque,defaultdict
import subprocess
import more_itertools as mit #type:ignore
import itertools as it
import logging
import time
from datetime import timedelta
from custom_logger import MyLogger,setup_logger
logger:MyLogger
FALSE_POSITIVES = set(['mall'])
THRESHOLDS = {
    4:3,
    3:5,
    2:5,
}

LEVEL_2_CHARS:list[tuple[str,str]] = [
    ('e','C'),

    ('l','T'),
    ('l',"R"),
    ('l',"I"),
    ('t','L'),
    ('i','L'),
    ('r','W'),
    ('v','W'),
    ('v','U'),
    ('ld',"B"),
    ('t',"R"),
    
    
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
    ("lil", "M"),
    ('ltl','M'),
    ("nl", "M"),
    ("ill","M"),
    ("rn","M"),

    ("ln", "M"),
    ('zn','M'),
    ('nz',"M"),
    ('ul',"M"),
    ('lu',"M"),
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

e=math.e



def apply_t(s, new, i, match_length) -> str:
    """Replace only the matched substring at index i based on its length."""
    return s[:i] + new + s[i + match_length:] 

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
def known_enough(word:str,threshold:float)->tuple[bool,float]:
    zfreq = zipf_frequency(word,'en')
    return zfreq>THRESHOLDS.get(len(word),threshold), zfreq



def run_cycle(unknown_words: set[str], chars: list[tuple[str, str]], known_corrections, max_iteration: int, logger, G: DiGraph, threshold=math.e):
    transformed_chars = [(rf"(?=({old}))", new) for old, new in chars]
    logger.info("Initiating unknown words in graph")
    results = {}
    new_words_for_next_iter = deque(unknown_words)

    for word in unknown_words:
        G.add_node(word, root=word, final=None, last_change_iter=0, match_word=word)
    if max_iteration == -1:
        max_iteration = 100
    
    current_iter = 0
    any_change = True
    start_time = time.time()
    
    try:
        while current_iter < max_iteration:
            any_change = False
            start_results = len(results)
            current_iter += 1
            iter_start_time = time.time()
            logger.notice("Starting iteration %s", current_iter)

            to_remove = set()
            next_char_queue = new_words_for_next_iter
            new_words_for_next_iter = deque()

            for old, new in transformed_chars:
                char_start_time = time.time()
                logger.info("Processing character replacement: %s -> %s", old, new)
                char_queue = next_char_queue
                next_char_queue = deque()

                while char_queue:
                    node_word = char_queue.popleft()
                    node_data = G.nodes[node_word]
                    match_word = node_data['match_word']
                    root = node_data["root"]

                    if node_data['last_change_iter'] < current_iter - 1 and not node_data['final']:
                        logger.info("%s not changeable, continuing and removing", node_word)
                        to_remove.add(node_word)
                        continue

                    if root in results:
                        continue

                    node_solved = False
                    matches = [(m.start(1), len(m.group(1))) for m in re.finditer(old, match_word)]
                    i = None
                    for i, match_length in matches:
                        any_change = True
                        new_match = apply_t(node_word, new, i, match_length)
                        new_word = new_match.lower()
                        if new_word in FALSE_POSITIVES:
                            continue
                        if new_word not in G:
                            known, zfreq = known_enough(new_word, threshold)
                            previously_corrected = known_corrections.get(new_word)

                            if previously_corrected:
                                logger.info("Previously corrected: '%s' -> '%s'", root, previously_corrected)
                                node_data["final"] = previously_corrected
                                G.add_node(new_word, root=root, final=previously_corrected, match_word=new_match, last_change_iter=current_iter)
                                results[root] = previously_corrected
                                node_solved = True
                            elif known:
                                results[root] = new_word
                                node_data["final"] = new_word
                                G.add_node(new_word, root=root, final=new_word, freq=zfreq, match_word=new_match, last_change_iter=current_iter)
                                node_solved = True
                                logger.info("New valid word: '%s' (freq: %.2f)", new_word, zfreq)
                            else:
                                G.add_node(new_word, root=root, final=None, freq=zfreq, match_word=new_match, last_change_iter=current_iter)
                                new_words_for_next_iter.append(new_word)
                                logger.debug("Added to graph: %s", new_word)
                            G.add_edge(node_word, new_word, old=old, new=new, i=i)

                        else:
                            found_node = G.nodes[new_word]
                            final = found_node.get("final")
                            if final:
                                results[root] = final
                                node_data["final"] = final
                                node_solved = True
                            elif not G.has_edge(node_word, new_word):
                                found_node['match_word'] = combine_match(new_match, found_node['match_word'])
                                G.add_edge(node_word, new_word, old=old, new=new, i=i)

                        if node_solved:
                            break
                    
                    if i is not None:
                        node_data['last_change_iter'] = current_iter
                    next_char_queue.append(node_word)
                
                char_end_time = time.time()
                logger.info("Processed '%s -> %s' in %.2f seconds", old, new, char_end_time - char_start_time)

            logger.notice("%d results found in iteration %d, total %d", len(results) - start_results, current_iter, len(results))
            prune_graph(G, results, next_char_queue, new_words_for_next_iter, logger)
            if not any_change:
                logger.notice("Ending at iteration %d due to lack of change", current_iter)
                break
            
            iter_end_time = time.time()
            logger.info("Iteration %d completed in %.2f seconds", current_iter, iter_end_time - iter_start_time)
        
    except KeyboardInterrupt:
        logger.notice("Keyboard interrupt at iteration %s", current_iter)
    finally:
        total_time = time.time() - start_time
        logger.info("Total runtime: %.2f seconds", total_time)
        still_out_there = {x for x in unknown_words if x not in results}
        logger.info("Total results: %d", len(results))
        clean_unconnected_nodes(G, results, logger)
        return G, results, still_out_there


def check_nodes(G:DiGraph,results:dict,logger):
    possible_children:dict[str,list[tuple[str,float]]] = defaultdict(list)
    for node,node_data in G.nodes(data=True):
        root = node_data.get('root')
        if root in results:
            continue
        freq = node_data.get("freq",zipf_frequency(node,'en'))
        if freq>0:
            logger.info("Possible word '%s' found for '%s'",node, root)
            possible_children[root].append((node,freq))
    return {root: sorted(v,key=lambda x: x[1],reverse=True) for root,v in possible_children.items() if len(v)>0}

def combine_match(str1:str,str2:str):
    return "".join([s.upper() if (str1[i].isupper() or str2[i].isupper()) else s for i,s in enumerate(str1)])


def main():
    os.chdir("/Users/BeckyMarcusMacbook/Thesis/TextCleaning/")

    home_dir = "networking/"
    log_file_path = "networking/networking.log"
    logger = setup_logger(log_file_path,notes =input("Note: "),overwrite=True)

    unknown_words_file = "networking/still_out_there.txt"
    with open(unknown_words_file,'r') as f:
        unknown_words = set([word.strip() for word in f.readlines()])
    logger.notice("Starting with %d unknown words",len(unknown_words))

    results1_file = "leftover_corrections1.json"
    results2_file= "leftover_corrections2.json"

    results_all_file = "all_results_leftover.json"

    still_unknown_after_file = "still_out_there21.txt"

    possible_children_path = "networking/children_list_unedited.json"

    manual_corrections_path = '/Users/BeckyMarcusMacbook/Thesis/TextCleaning/networking/results_FINAL.json'


    manual_corrections = json.load(open(manual_corrections_path,'r'))
    G=DiGraph()
    unknown_words, results1, still_out_there = run_cycle(unknown_words,LEVEL_1_CHARS,manual_corrections,-1,logger,G)
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


    relevant_unknown,results2,still_still_out_there  = run_cycle(still_out_there,LEVEL_2_CHARS,known_corrections,-1,logger,G)
    results2_updated = {k:known_corrections.get(v,v) for k,v in results2.items()}

    save2 = os.path.join(home_dir,results2_file)
    with open(save2,'w') as file:
        file.write(simplejson.dumps(results2_updated,indent="\t",sort_keys=True))
    all_results = {**results2_updated,**results1_updated,}
    logger.notice("Total %d results out of %d",len(all_results),len(unknown_words))

    logger.notice("Looking for infrequent words in graph now")

    possible_children = check_nodes(G,{**all_results,**manual_corrections},logger)

    with open(possible_children_path,'w') as f:
        f.write(simplejson.dumps(possible_children,sort_keys=True))

    totally_unknown = set(still_still_out_there)-set(possible_children)

    logger.info("%d root words with no known children",len(totally_unknown))
    with open(still_unknown_path,'w') as f:
            f.write("\n".join(totally_unknown))
    results_all_path = os.path.join(home_dir,results_all_file)
    with open(results_all_path,'w') as f:
        f.write(simplejson.dumps(all_results,item_sort_key=lambda item:item[1],indent="\t"))



    

if __name__=="__main__":

    main()