from typing import Callable
import json
import os
import networkx as nx #type:ignore
from networkx import DiGraph #type:ignore
from wordfreq import zipf_frequency
import math
import re
from collections import deque
import more_itertools as mit #type:ignore
import itertools as it
import logging
import time
from datetime import timedelta
from custom_logger import MyLogger,setup_logger
logger:MyLogger

LEVEL_2_CHARS:list[tuple[str,str]] = [
    ('l','T'),
    ('l',"R"),
    ('l',"I"),
    ('t','L'),
    ('i','L'),
    
    ('e','C'),
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

def run_cycle(unfixed_dir:str,chars:list[tuple[str,str]],prelim_known,max_iteration:int,logger:MyLogger):
    char_set = set([char[0] for char in chars])
    pattern = re.compile("|".join([fr"\b[A-Za-z]*{char}[A-Za-z]*\b" for char in char_set]))
    print("Getting unknown words")
    unknown_words,all_words = get_unknown_words(unfixed_dir,pattern,prelim_known)

    logging.info("Initiating known words in graph")
    G=DiGraph()
    results ={}
    new_words_for_next_iter = deque()
 #put in the new queue
    print("Initiating graph")
    for word in unknown_words:
        G.add_node(word,
                   root=word,
                   final = None,
                   level = 0,
                    )
        new_words_for_next_iter.append(word)
    #results.clear()
    current_iter=0
    while current_iter<max_iteration:
        current_iter+=1
        logger.notice("Starting iteration %s",current_iter)

        results_gotten=deque()
        next_char_queue = new_words_for_next_iter
        new_words_for_next_iter = deque()

        
        for old,new in chars:
            logger.info("Chars %s to %s",old,new)
            char_queue = next_char_queue
            next_char_queue=deque()
            logger.info("In queue: %s",len(char_queue))

            while char_queue:
                node_word = char_queue.pop()
                #logger.debug("Working with %s",node_word)
                node_data = G.nodes[node_word]
                root = node_data.get("root")
                if root in results:
                    continue 
                node_solved=False
                i = None
                for i in mit.locate(node_word,pred = lambda *x: mit.iequals(x,old),window_size=len(old)) if new!="" else [-1]:
                    new_match:str|None = apply_t(node_word,old,new,i)
                    new_word = new_match.lower()
                    if not new_word in G:
                        known, zfreq = known_enough(new_word)
                        
                        if known or new_word in prelim_known:
                            results.update({root:new_word})
                            node_data.update({"final":new_word})
                            G.add_node(new_word,
                                       root=root,
                                       final=new_word,
                                       freq=zfreq,)
                            results_gotten.append(new_word)
                            
                            node_solved = True
                            logger.info("SUCCESS - Likely found a new word: '%s' with frequency %.2f",new_word,zfreq)
                            G.add_edge(node_word,new_word,old=old,new=new,i=i)
                        else:
                            logger.debug("Added %s to graph",new_word)

                            G.add_node(new_word,
                                       root=root,
                                       final=new_word,
                                       freq=zfreq,)
                            new_words_for_next_iter.append(new_word)
                            node_solved = False
                            G.add_edge(node_word,new_word,old=old,new=new,i=i)
                        assert node_word in [*G.predecessors(new_word)]
                    else:
                        new_word_node = G.nodes[new_word]
                        final = new_word_node.get('final')

                        if final is not None:
                            logger.info("Made new word '%s' that connects to known word '%s'",new_word,final)
                            results.update({root:final})
                            node_data.update({'final':final})
                            node_solved=True
                        elif not G.has_edge(node_word,new_word):
                            G.add_edge(node_word,new_word,old=old,new=new,i=i)
                            node_solved=False
                    if node_solved:
                        
                        break
                
                next_char_queue.append(node_word)

        ## end of iteration

        # gotten = deque(results.values())
        # def recurse_and_remove(real_word:str,to_remove_from_queue):
        #     nonlocal printed
        #     assert real_word in G
        #     preds= G.pred[new_word]
        #     n = G[real_word]
        #     for _,accessible_words in nx.predecessor(G,real_word,)
        #         if not printed:
        #             print(accessible_words)
        #             printed=True
        #         for accessible_word in accessible_words:

        #             if accessible_word in gotten:
        #                 gotten.remove(accessible_word)
        #                 recurse_and_remove(accessible_word,to_remove_from_queue)
        #             elif accessible_word in to_remove_from_queue:
        #                 continue
        #             else:
        #                 d = G.nodes[accessible_word]
        #                 d.update({final:real_word})
        #                 to_remove_from_queue.add(accessible_word)
        #     assert printed
        # print(f"in results gotten: {len(gotten)}")
        # while gotten:
        #     real_word=gotten.pop()
        #     recurse_and_remove(real_word,to_remove_from_queue)
        
        # logger.notice("Removing %s from queue because they're in results",len(to_remove_from_queue))
        # for word in to_remove_from_queue:

        #     new_words_for_next_iter.remove(word)
    still_out_there = set([x for x in unknown_words if x not in results])
    print(f"Total results: {len(results)}")
    return unknown_words,results, still_out_there

def main():
    log_file_path = "./networking.log"
    unfixed_dir = "manual_work/E2/problematic_unfixed"
    note = "First run fingers crossed"
    save_path = "corrections1.json"
    logger = setup_logger(log_file_path,note,overwrite=True)
    manual_corrections = json.load(open('manual_work/corrections.json','r'))
    prelim_known = set([*manual_corrections.values()])
    unknown_words, results, still_out_there = run_cycle(unfixed_dir,LEVEL_1_CHARS,prelim_known,5,logger)
    results_updated = {k:results.get(v,v) for k,v in manual_corrections.items()}
    known_corrections = {**manual_corrections,**results_updated}
    json.dump(results,open(save_path,'w'))
    prelim_known.update(results.keys())
    save2="./corrections2.json"
    relevant_unknown,results2,still_still_out_there  = run_cycle(unfixed_dir,LEVEL_2_CHARS,known_corrections.keys(),4,logger)
    results2_updated = {k:known_corrections.get(v,v) for k,v in results2.items()}
    json.dump(results2_updated,open(save2,'w'))
    with open("still_out_there.txt",'w') as f:
            f.writelines("\n".join(still_still_out_there))
    

if __name__=="__main__":
    # import sys
    # if len(sys.argv) != 2:
    #     print("Usage: python text_cleaning.py <source_dir> <dest_dir> <log_file> <commit_changes>")
    #     sys.exit(1)

    # unfixed_dir = sys.argv[1]
    # save_path = sys.argv[2]

    main()