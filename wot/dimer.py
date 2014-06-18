#!/usr/bin/env python


import sys
import fileinput
import itertools

ALPHABET = ("A", "C", "G", "T")


def sequence_count(string, wordlength):
    """Return a frequency count of all sequences of a given size found in a string.
    
    
    """
    i = 0
    wc = {}
    while i < len(string) - wordlength + 1:
        word = string[i:i+wordlength]
        if word in wc:
            wc[word] += 1
        else:
            wc[word] = 1
        i += 1
    return wc



def pretty_print(wordcount_dict, wordlength):
    """This prints out the wordcount index in order to mimic the R1.BAS output format.
    """
    output = ""
    e = 0
    for w in itertools.product(ALPHABET, repeat=wordlength):
        w = ''.join(w)
        try:
            output += "%3.10s%13s\n" % (e, wordcount_dict[w])
        except IndexError:
            output += "%s\t0\n"
        e += 1
    return output

def histogram(filename, wordlength):
    """Returns a histogram report that meets NIHCC's format.

    This function returns a string that is compatible with the example code
    used Jim Deleo's Scientific Computing group at the NIH Clinical Center.
    'Pick a standard, any standard', we'll we've agreed to use this.
    """
    wc = {}
    for line in open(filename).readlines():
        wcnew = sequence_count(line, wordlength)
        wc = {i: wc.get(i, 0) + wcnew.get(i, 0) for i in set(wc) | set(wcnew)}
    return pretty_print(wc, wordlength)

    
if __name__ == "__main__":
    print histogram(sys.argv[1], 3)

