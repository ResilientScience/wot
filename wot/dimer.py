#!/usr/bin/env python


import sys
import fileinput


ALPHABET = ["A", "C", "G", "T"]


def sequence_count(lines, wordlength):
    wordcount = {}
    c0 = None
    for line in lines:
        for c in line:
            if not c0:
                c0 = c
            else:
                word = c0 + c
                c0 = c
                if word in wordcount:
                    wordcount[word] += 1
                else:
                    wordcount[word] = 1
    return wordcount


def pretty_print(wordcount_dict, wordlength):
    """This prints out the wordcount index in order to mimic the R1.BAS output format.
    """
    output = ""
    e = 0
    for w in [j+i for j in ALPHABET for i in ALPHABET]:
        try:
            output += "%3.10s%13s\n" % (e, wordcount_dict[w])
        except IndexError:
            output += "%s\t0\n"
        e += 1
    return output

def histogram(filename):
    wc = sequence_count(open(filename).readlines(), 2)
    return pretty_print(wc, 2)    
    
if __name__ == "__main__":
    wc = sequence_count(fileinput.input(filename), 2)
    print pretty_print(wc, 2)    


