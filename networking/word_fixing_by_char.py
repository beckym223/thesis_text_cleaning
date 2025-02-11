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
import argparse
from concurrent.futures import ThreadPoolExecutor
import threading
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
        return results, still_out_there


def run_cycle_efficient(unknown_words: set[str], chars: list[tuple[str, str]], known_corrections, max_iteration: int, logger, G: nx.DiGraph, threshold=math.e):
    transformed_chars = [(re.compile(rf"(?=({old}))"), new) for old, new in chars]
    logger.info("Initiating unknown words in graph")
    results = {}
    new_words_for_next_iter = deque(unknown_words)
    word_lock = threading.Lock()

    for word in unknown_words:
        G.add_node(word, root=word, final=None, last_change_iter=0, match_word=word)
    
    if max_iteration == -1:
        max_iteration = 100
    
    current_iter = 0
    start_time = time.time()
    
    try:
        while current_iter < max_iteration:
            start_results = len(results)
            current_iter += 1
            iter_start_time = time.time()
            logger.notice("Starting iteration %s", current_iter)
            
            next_char_queue = new_words_for_next_iter
            new_words_for_next_iter = deque()
            
            # Group words by length to minimize interference
            word_batches = defaultdict(list)
            for word in next_char_queue:
                word_batches[len(word)].append(word)
            
            with ThreadPoolExecutor() as executor:
                futures = []
                
                for _, batch in word_batches.items():
                    futures.append(executor.submit(process_batch, G, batch, transformed_chars, results, new_words_for_next_iter, known_corrections, threshold, current_iter, logger, word_lock))
                
                for future in futures:
                    future.result()
            
            logger.notice("%d results found in iteration %d, total %d", len(results) - start_results, current_iter, len(results))
            
            if not new_words_for_next_iter:
                logger.notice("Ending at iteration %d due to lack of change", current_iter)
                break
            
            iter_end_time = time.time()
            logger.info("Iteration %d completed in %.2f seconds", current_iter, iter_end_time - iter_start_time)
        
    except KeyboardInterrupt:
        logger.notice("Keyboard interrupt at iteration %s", current_iter)
    finally:
        total_time = time.time() - start_time
        logger.info("Total runtime: %.2f seconds", total_time)
        return results, {x for x in unknown_words if x not in results}

def process_batch(G, batch, transformed_chars, results, new_words_for_next_iter, known_corrections, threshold, current_iter, logger, word_lock):
    """Parallelized function to process a batch of words."""
    batch_nodes = []
    
    for node_word in batch:
        node_data = G.nodes[node_word]
        match_word = node_data['match_word']
        root = node_data["root"]
        
        if root in results:
            continue
        
        for old_regex, new in transformed_chars:
            matches = [(m.start(1), len(m.group(1))) for m in old_regex.finditer(match_word)]
            
            for i, match_length in matches:
                new_match = apply_t(node_word, new, i, match_length)
                new_word = new_match.lower()
                
                if new_word not in G:
                    known, zfreq = known_enough(new_word, threshold)
                    previously_corrected = known_corrections.get(new_word)
                    
                    if previously_corrected:
                        with word_lock:
                            results[root] = previously_corrected
                        batch_nodes.append((new_word, root, previously_corrected, new_match, current_iter))
                    elif known:
                        with word_lock:
                            results[root] = new_word
                        batch_nodes.append((new_word, root, new_word, new_match, current_iter, zfreq))
                    else:
                        batch_nodes.append((new_word, root, None, new_match, current_iter, zfreq))
                        with word_lock:
                            new_words_for_next_iter.append(new_word)
                    
                    G.add_edge(node_word, new_word, old=old_regex.pattern, new=new, i=i)
                else:
                    found_node = G.nodes[new_word]
                    final = found_node.get("final")
                    if final:
                        with word_lock:
                            results[root] = final
    
    # Batch update graph nodes
    for new_word, root, final, match_word, last_change_iter, *freq in batch_nodes:
        G.add_node(new_word, root=root, final=final, match_word=match_word, last_change_iter=last_change_iter, freq=freq[0] if freq else None)

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

def make_pattern(*char_list):
    char_set = {char[0] for char in it.chain(*char_list)}  # Using set comprehension for efficiency
    return re.compile("|".join(fr"\b[A-Za-z]*{re.escape(char)}[A-Za-z]*\b" for char in char_set))

def get_unique_dir(base_dir):
    """Generates a unique directory name by appending a number if it already exists."""
    if not os.path.exists(base_dir):
        return base_dir  # Return the original if it doesn’t exist

    counter = 1
    while True:
        new_dir = f"{base_dir}_{counter}"
        if not os.path.exists(new_dir):
            return new_dir
        counter += 1

def main(run_save_dir, unknown_words_path, manual_corrections_path, read_dir=False):
    # Convert paths to absolute based on execution location
    run_save_dir = os.path.abspath(run_save_dir)
    unknown_words_path = os.path.abspath(unknown_words_path)
    manual_corrections_path = os.path.abspath(manual_corrections_path)

    # Ensure save directory is unique
    run_save_dir = get_unique_dir(run_save_dir)
    os.makedirs(run_save_dir, exist_ok=True)

    log_file_path = os.path.join(run_save_dir,'word_correcting.log')
    logger = setup_logger(log_file_path,notes =input("Note: "),overwrite=True)


    semi_results_file = os.path.join(run_save_dir,"cycle_corrections.json")

    results_all_file = os.path.join(run_save_dir,"all_results.json")

    still_unknown_after_file = os.path.join(run_save_dir,"remaining_after_cycle.txt")

    final_unknown_file = os.path.join(run_save_dir,"remaining_after_run.txt")

    possible_children_path = os.path.join(run_save_dir,"children_list_unedited.json")

    known_corrections = json.load(open(manual_corrections_path,'r'))
    

    param_cycle = [(LEVEL_1_CHARS,-1),
                    (LEVEL_2_CHARS,-1)
                   ]
    if read_dir:
        logger.info("Getting unknown words from directory %s",unknown_words_path)
        pattern = make_pattern(*[param[0] for param in param_cycle])
        unknown_words, _ =get_unknown_words(unknown_words_path,pattern,set(known_corrections.keys()))
    else:
        logger.info("reading unknown words from file %s",unknown_words_path)
        with open(unknown_words_path,'r') as f:
            unknown_words = set([word.strip() for word in f.readlines()])
# /Users/BeckyMarcusMacbook/Thesis/TextCleaning/manual_work/corrections.json

    logger.notice("Starting with %d unknown words",len(unknown_words))
    all_results = {}
    G=DiGraph()
    for i, (char_corrections ,max_iter) in enumerate(param_cycle):
        current_results, still_out_there = run_cycle_efficient(unknown_words,char_corrections,known_corrections,max_iter,logger,G)
        unknown_words=still_out_there
        results_updated = {k:known_corrections.get(v,v) for k,v in current_results.items()}
        
        still_unknown_path = number_path(still_unknown_after_file,i)
        with open(still_unknown_path,'w') as f:
                for l in still_out_there:
                    if l in results_updated:
                        logger.info("%s is not still out there, we got it",l)
                    else:
                        f.write(f"{l}\n")
        known_corrections.update(results_updated)
        result_save_path = number_path(semi_results_file,1)
        with open(result_save_path,'w') as file:
            file.write(simplejson.dumps(results_updated,indent="\t",sort_keys=True))
        logger.info("Saving %d results in cycle %d",len(results_updated),i)
        all_results = {**results_updated,**all_results}

    logger.notice("Looking for infrequent words in graph now")

    possible_children = check_nodes(G,known_corrections,logger)

    with open(possible_children_path,'w') as f:
        f.write(simplejson.dumps(possible_children,sort_keys=True,indent='\t'))

    totally_unknown = set(unknown_words)-set(possible_children)

    logger.info("%d root words with no known children",len(totally_unknown))
    with open(final_unknown_file,'w') as f:
            f.write("\n".join(totally_unknown))

    with open(results_all_file,'w') as f:
        f.write(simplejson.dumps(all_results,item_sort_key=lambda item:item[1],indent="\t"))



def number_path(path,number):
    try:
        front,dot_txt = path.rsplit(".",1)
    except:
        logger.error("Could not properly split %s",path)
        raise
    return f"{front}{number:02}.{dot_txt}"

if __name__=="__main__":

    parser = argparse.ArgumentParser(description=f"Process text data with specified paths")
    parser.add_argument("run_save_dir", help="Directory to save the run results")
    parser.add_argument("unknown_words_path", help="Path to the unknown words file")
    parser.add_argument("manual_corrections_path", help="Path to the manual corrections file")
    parser.add_argument("--read_dir", action="store_true", help="Flag to indicate reading directory")

    args = parser.parse_args()
    main(args.run_save_dir, args.unknown_words_path, args.manual_corrections_path, args.read_dir)