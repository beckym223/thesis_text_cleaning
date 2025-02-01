import os
import re
import json
import more_itertools as mit


def match_case(original, replacement):
    """
    Adjust the replacement text to match the case of the original text.
    """
    if original.isupper():
        return replacement.upper()
    elif original.istitle():
        return replacement.title()
    elif original.islower():
        return replacement.lower()
    else:
        return replacement


def fix_text(text:str,results:dict[str,str]):

    tokens = set(re.findall(r"\b.+?\b",text))
    def get_pattern_replacement(t):
        fix1 =re.sub("1",'l',t).lower()
        m = results.get(fix1)
        if m is None:
            return m
        return (rf"([^\w])({t})([^\w])",f"\1**{match_case(t,m)}**\3")

    
    for pattern,rep in mit.filter_map(get_pattern_replacement,tokens):
        text = re.sub(pattern,rep,text)
    return text

def main():
    os.chdir("/Users/BeckyMarcusMacbook/Thesis/TextCleaning/")
    results = json.load(open('/Users/BeckyMarcusMacbook/Thesis/TextCleaning/networking/results_FINAL.json'))
    start_dir = "/Users/BeckyMarcusMacbook/Thesis/TextCleaning/manual_work/E2/problematic_unfixed"
    save_dir = "manual_work/E2/problematic_fixed"
    for file in sorted(os.listdir(start_dir)):
        with open(os.path.join(start_dir,file)) as f:
            text=f.read()
        new_text = fix_text(text,results)
        with open(os.path.join(save_dir,file),'w') as f:
            f.write(new_text)


if __name__=="__main__":
    main()



