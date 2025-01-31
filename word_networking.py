from typing import Callable,Any
import os
import networkx as nx #type:ignore
from networkx import DiGraph #type:ignore
from wordfreq import zipf_frequency
import math
import re
from collections import deque, defaultdict
import more_itertools as mit #type:ignore
import itertools as it
import logging
import time
from datetime import timedelta
from custom_logger import MyLogger
logger:MyLogger
"""

# init new_words_for_next_iter
# while iteration less than current iter:
#     results_gotten = deque 
#     next_char queue = new_words_for_next_iter
#     for char in chars:
#         clear next iter queue
#         while queue for chars:
            
#             if the root node it's connected to is in results:
#                 continue 
                
#             for all of the changes we can make:
#                 get new word
#                 if it's not on the graph:
#                     if it's not real:
#                         add to graph
#                         add node connecting previous one that we're working on
#                         add to next iter queue
#                         node solved= false
#                     if it's real:
#                         update results
#                         update old node as connected to final
#                         make node and edge
#                         add new word to results gotten
#                         node solved=true
#                 if it's in the graph and connected to a known word:
#                     update results
#                     node solved=True
#                 else:
#                     connect nodes
#                     node sovled= False
#                 if node solved:
#                     break
#             if not node_solved:
#                 add to next char queue
                    


                    
                        
                    




            if we got the end state:
                add resulting word to results gotten in iter
            
            else
                put word in next char queue
    AT the end of the iter

    recursively:
    while results gotten:
        pop result
        update nodes on path, to depth current iteration+1


                


    """
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

def iterate_word(G:DiGraph,
                 current_iter:int,
                 node_word:str,
                 match_word:str,
                 old:str,
                 new:str,
                 og:str,
                 root_words:set,
                 node_data:dict[str,Any],
                 next_iter_queue:deque[str],
                 results:dict[str,str],
                 )->tuple[bool,bool,bool]:
    
    node_data = G.nodes[node_word]
    match_word = node_data['match_word']
    og = node_data['root']
    root_words = node_data['root_unknown_words']
    
    i=None
    node_solved=False
    new_edge = False
    for i in mit.locate(match_word,pred = lambda *x: mit.iequals(x,old),window_size=len(old)) if new!="" else [-1]:
        new_match:str|None = apply_t(node_word,old,new,i)
        new_word = new_match.lower()
        if not new_word in G:
            known, zfreq = known_enough(new_word)
            if known:
                logger.info("SUCCESS - Likely found a new word: %s with frequency %.2f",new_word,zfreq)
                G.add_node(new_word,root_unknown_words=root_words,final=new_word,root=og,originally_known=False,freq=zfreq,last_change=current_iter,match_word=new_match)
                node_solved=True
                logger.debug("Updating results for %d roots")
                results.update({root:new_word for root in root_words})

            else:
                logger.debug("Adding new word %s to graph and next next queue",new_word)
                G.add_node(new_word,root_unknown_words=root_words,final=None,root=og,originally_known=False,freq=zfreq,last_change=current_iter,match_word=new_match)
                next_iter_queue.append(new_word)
        elif not G.has_edge(node_word,new_word):
            new_word_node = G.nodes[new_word]
            new_word_roots:set = new_word_node['root_unknown_words'] #update so they share roots, only the first time they have an edge, however
            root_words.update(new_word_roots)
            final = new_word_node['final']

            if final is not None:
                logger.info("SUCCESS - Created word %s from %s which connects to real word %s",new_word, node_word,final )
                node_data.update({'final':final})

                results.update({root:final for root in root_words})
                node_solved=True
            else:
                logger.debug("%s in graph but not a final word, updating root words for next iteration")
                new_word_roots.update(root_words)
        else:
            logger.info("%s already connected to %s, continuing")
        if not G.has_edge(node_word,new_word):
            G.add_edge(node_word,new_word,old=old,new=new,idx=i)
            new_edge=not G.has_edge(new_word,node_word)
        if node_solved:
            return True,True,True
    
    return i is not None,False, new_edge

def word_correcting(unknown_words:set[str],
                    chars:list[tuple[str,str]],
                    max_iteration:int,
                    start_G:None|DiGraph= None,
                    start_results:dict[str,str]|None=None,
                    ):
                    #)->tuple[dict[str,str],set[str],DiGraph]:
    pass


def run_cycle(name:str,unfixed_dir,chars,prelim_known,max_iteration,logger:MyLogger):
    char_set = set([char[0] for char in chars])
    pattern = re.compile("|".join([fr"\b[A-Za-z]*{char}[A-Za-z]*\b" for char in char_set]))
    unknown_words = get_unknown_words(unfixed_dir,pattern,prelim_known)

    logging.info("Initiating known words in graph")
    next_iter_queue_for_word: dict[str,deque] = defaultdict(deque)
    G=DiGraph()
    results ={}
    nodes = set()
    new_words_for_next_iter = deque()
 #put in the new queue
    for word in unknown_words:
        G.add_node(word,
                   root=word,
                   final = None,
                   level = 0,
                    )
        new_words_for_next_iter.append(word)
    run_start = time.monotonic()
    made_change=True
    #results.clear()
    current_iter=0
    while current_iter<max_iteration:
        current_iter+=1
        results_gotten=deque()
        next_char_queue = new_words_for_next_iter
        for old,new in chars:
            new_words_for_next_iter.clear()
            while next_char_queue:
                node_word = next_char_queue.pop()
                node_data = G.nodes[node_word]
                root = node_data.get("root")
                if root in results:
                    continue 
                node_solved=False
                for i in mit.locate(node_word,pred = lambda *x: mit.iequals(x,old),window_size=len(old)) if new!="" else [-1]:
                    new_match:str|None = apply_t(node_word,old,new,i)
                    new_word = new_match.lower()
                    if not new_word in G:
                        known, zfreq = known_enough(new_word)
                        
                        if known:
                            results.update({root:new_word})
                            node_data.update({"final":new_word})
                            G.add_node(new_word,
                                       root=root,
                                       final=new_word,
                                       freq=zfreq,)
                            results_gotten.append(new_word)
                            node_solved = True
                            logger.info("SUCCESS - Likely found a new word: %s with frequency %.2f",new_word,zfreq)

                        else:
                            G.add_node(new_word,
                                       root=root,
                                       final=new_word,
                                       freq=zfreq,)
                            new_words_for_next_iter.append(new_word)
                            node_solved = False
                        G.add_edge(node_word,new_word,old=old,new=new,i=i)
                    else:
                        new_word_node = G.nodes[new_word]
                        final = new_word_node.get('final')

                        if final is not None:
                            results.update({root:final})
                            node_data.update({'final':final})
                            node_solved=True
                        elif not G.has_edge(node_word,new_word):
                            G.add_edge(node_word,new_word,old=old,new=new,i=i)
                            node_solved=False
                    if node_solved:
                        break
                    else:
                        next_char_queue.append(node_word)
        ## end of iteration
        to_remove_from_queue=set()
        
        def recurse_and_remove(real_word:str):
            for _, accessible_word in nx.bfs_predecessors(G,real_word,current_iter):
                if accessible_word in results_gotten:
                    results_gotten.remove(accessible_word)
                    recurse_and_remove(accessible_word)
                elif accessible_word in to_remove_from_queue:
                    continue
                else:
                    d = G.nodes[accessible_word]
                    d.update({final:real_word})
                    to_remove_from_queue.add(accessible_word)

        while results_gotten:
            real_word = results_gotten.pop()
            recurse_and_remove(real_word)
        for word in to_remove_from_queue:
            new_words_for_next_iter.remove(word)


    logger.info("Max iteration: %d",max_iteration)
    start_unknown_ct = len(unknown_words)
    next_char_queue = deque() #will include any words that aren't ended
    dead_leaves = set()
    try:
        while current_iter<max_iteration:
            dead_leaves=0
            current_iter_queue = next_iter_queue+next_char_queue
            it_start_time = time.monotonic()
            current_iter+=1
            logger.notice("Starting Iteration %s",current_iter)
            info = {
                'nodes':G.number_of_nodes(),
                'edges':G.number_of_edges(),
                'results':len(results),
                'time':time.monotonic()
            }
            n_nodes_start = G.number_of_nodes()
            n_edges_start = G.number_of_edges()
            results_start = len(results)
            logger.notice("Starting with %d in queue - %d nodes and %d edges",len(current_iter_queue),n_nodes_start,n_edges_start)
            next_char_queue = current_iter_queue
            newly_found=deque()
            for old,new in chars:
                ## Start Char
                char_start = time.monotonic()
                current_char_queue=next_char_queue
                next_char_queue = deque()
                logger.info("Replacing '%s' with '%s'",old,new)
                start_result = len(results)
                start_nodes = G.number_of_nodes()
                start_edges = G.number_of_edges()
                #print(f"In results: {len(results)} out of {len(unknown_words)}")
                while current_char_queue:
                    ### Start Word
                    node_word = current_char_queue.pop()
                    node_solved=False
                    data:dict[str,Any]= G.nodes[node_word]
                    # final = results.get(og)
                    final=data.get('eventual_real_word')
                    if final is not None: #means that you have a path to a solution
                        # bestie should not be in the queue
                        continue
                    if not data.get('reachable_by_real_word',set()).issubset(set(results.keys())):
                        #means that all of the results its connected to have already been found
                        data.update({'active':False})

                    if data['last_change']<current_iter-1:
                        #means it can't be chagned anymore
                        logging.info("%s can't be changed further")
                        dead_leaves += 1
                    any_change, node_solved_word = iterate_word(G,current_iter,node_word,old,new,og,root_words,data,next_iter_queue)
                    
                    if node_solved_word is not None:
                        newly_found.append(node_solved_word)
                        logger.debug("Continuing to next node word")
                        continue
                    if not any_change:
                        logger.debug("'%s' not found in '%s', putting back in queue",old,node_word)
                    else:
                        logger.debug("No known word found for %s, putting back in queue",node_word)
                        data.update({'last_change':current_iter})

                    next_char_queue.append(node_word)
                    ### End word


                char_elapsed = timedelta(seconds = time.monotonic()-char_start)
                char_edge_diff= G.number_of_edges() - start_edges
                char_node_diff = G.number_of_nodes() - start_nodes
                logger.info("Iteration %d - '%s' to '%s' - Time: %s - Results Added: %d - Edges Added: %d - Nodes Added: %d",
                            current_iter,old,new,char_elapsed,len(results)-start_result,char_edge_diff,char_node_diff)
                ## End char
            #report_end_iter(iter_report_level,G,current_iter,it_start_time,n_nodes_start,n_edges_start)
     
                        


                    pred_node=G.nodes.get(accessible_word)
                    pred_node.update({
                        "final":newly_found,
                    })

            logger.notice("After iteration %d, %d results found",current_iter,len(results))
            # End Iteration
        if not made_change:
            print(f"No more changes made after iteration {current_iter}")
        

    except KeyboardInterrupt:
        reason = input("Reason for interrupting")
        logger.notice("Ending run: %s",reason)
        raise
    except Exception as e:
        logging.error("Error: %s",e)
        raise
    finally:
        elapsed = timedelta(seconds=time.monotonic() - run_start)
        still_out_there = [w for w in unknown_words if w not in results]

        logger.notice("Ran %d iterations over %s to get %d results out of %d",max_iteration,elapsed,len(results),start_unknown_ct )

def main():
    unknown_words,text_words = get_unknown_words()
    

if __name__=="__main__":
    results = {}
    logger = logging.getLogger()