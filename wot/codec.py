#! /usr/bin/env python
# ______________________________________________________________________
# requires bitarray: pip install bitarray

from wot.mrwot import Grammar
from collections import Counter
import sys, struct, bitarray, getopt

# ______________________________________________________________________

SIXTY4K = 65536
USAGE = """Usage:
    $ python -m wot.codec -cdh file1 [file2...]

Flags:

    -c    Output result to stdout (default is new file with '.wot'
          extension added for compression, removed for decompression).
    -d    Decompress (default is compress).
    -h    Print this help.
"""

# ______________________________________________________________________

def unigram(grammar):
    """Create a unigram histogram for both terminals and nonterminals
    in the input grammar."""
    ret_val = Counter()
    for rule in grammar.rules:
        if rule is not None:
            for symbol in rule.iter_symbols():
                symbol_val = symbol.dump()
                ret_val[symbol_val] += 1
    return ret_val

# ______________________________________________________________________

def build_tree(hist):
    """Build a prefix coding tree using counts in the input histogram.

    Sorts the work list each iteration, so should be inefficient for
    large inputs.
    """
    count_list = list((item[1], item[0]) for item in hist.items())
    count_list.sort()
    while len(count_list) > 1:
        left, right = count_list[:2]
        del count_list[:2]
        count = left[0] + right[0]
        node = count, (left[1], right[1])
        count_list.append(node)
        count_list.sort()
    return count_list[0][1]

# ______________________________________________________________________

def build_tree2(hist):
    """Build a prefix coding tree using counts in the input histogram.

    Should insert in-place, keeping the work list sorted.
    """
    count_list = list((item[1], item[0]) for item in hist.items())
    count_list.sort()
    count_list_len = len(count_list)
    while count_list_len > 1:
        left, right = count_list[:2]
        del count_list[:2]
        count_list_len -= 2
        count = left[0] + right[0]
        node = count, (left[1], right[1])
        idx = 0
        if idx < count_list_len:
            while idx < count_list_len and count > count_list[idx][0]:
                idx += 1
            while idx < count_list_len and node > count_list[idx]:
                idx += 1
        if idx < count_list_len:
            count_list.insert(idx, node)
        else:
            count_list.append(node)
        count_list_len += 1
    return count_list[0][1]

# ______________________________________________________________________

def build_prefix_code_map(tree):
    """Given a prefix coding tree, create a prefix coding map from
    terminal tree nodes to the corresponding bit coding.
    """
    ret_val = {}
    crnt = bitarray.bitarray()
    def _builder(node):
        bit = 0
        for child in node:
            crnt.append(bit)
            if type(child) is tuple:
                _builder(child)
            else:
                ret_val[child] = crnt.copy()
            bit += 1
            crnt.pop()
    _builder(tree)
    return ret_val

# ______________________________________________________________________

def encode_grammar(grammar):
    """Returns generator that outputs a compressed representation of
    the input grammar.
    """
    hist = unigram(grammar)
    tree = build_tree2(hist)
    code = build_prefix_code_map(tree)
    grammar_dict = {}
    offset_dict = {}
    max_symbol = 0
    offsets = []
    rhs = bitarray.bitarray()
    for rule in grammar.rules:
        if rule is not None:
            del rhs[:]
            rhs.encode(code, (sym.dump() for sym in rule.iter_symbols()))
            symbol_nr = rule.number
            rhs_bytes = rhs.tobytes()
            grammar_dict[symbol_nr] = rhs_bytes
            offsets.append(len(rhs_bytes))
            if symbol_nr > max_symbol:
                max_symbol = symbol_nr
    offsets.pop()
    yield "WOT\x00"
    single_int = struct.Struct("<I")
    yield single_int.pack(max_symbol)
    for byte_val in xrange(256):
        yield struct.pack("<I", hist[chr(byte_val)])
    for sym_nr in xrange(max_symbol + 1):
        yield struct.pack("<I", hist[sym_nr])
    yield struct.pack("<I", len(offsets))
    for offs in offsets:
        yield struct.pack("<I", offs)
    keys = grammar_dict.keys()
    keys.sort()
    for symbol_nr in keys:
        yield grammar_dict[symbol_nr]
    yield ''

# ______________________________________________________________________

def decode_grammar(stream):
    """Given a stream (file or file-like object), return a dictionary
    of the grammar rules (mapping from nonterminals to mixed lists of
    terminals and nonterminals.
    """
    hist = Counter()
    assert stream.read(4) == "WOT\x00"
    single_int = struct.Struct("<I")
    max_symbol = single_int.unpack(stream.read(4))[0]
    for byte_val in xrange(256):
        count = single_int.unpack(stream.read(4))[0]
        if count > 0:
            hist[chr(byte_val)] = count
    symbols = [0]
    for sym_nr in xrange(max_symbol + 1):
        count = single_int.unpack(stream.read(4))[0]
        if count > 0:
            hist[sym_nr] = count
            symbols.append(sym_nr)
    offsets = {}
    for sym_nr in symbols[:-1]:
        offsets[sym_nr] = single_int.unpack(stream.read(4))[0]
    tree = build_tree2(hist)
    code = build_prefix_code_map(tree)
    grammar_dict = {}
    #print >>sys.stderr, symbols[:-1]
    for sym_nr in symbols[:-1]:
        sym_str = stream.read(offsets[sym_nr])
        ba = bitarray.bitarray()
        ba.frombytes(sym_str)
        grammar_dict[sym_nr] = ba.decode(code)
    sym_str = stream.read()
    ba = bitarray.bitarray()
    ba.frombytes(sym_str)
    grammar_dict[symbols[-1]] = ba.decode(code)
    return grammar_dict

# ______________________________________________________________________

def encode(istream, ostream):
    grammar = Grammar()
    input_buf = istream.read(SIXTY4K)
    while len(input_buf) > 0:
        grammar.build(input_buf)
        input_buf = istream.read(SIXTY4K)
    for out_buf in encode_grammar(grammar):
        ostream.write(out_buf)
    ostream.flush()

# ______________________________________________________________________

def decode(istream, ostream):
    def _decoder(symbols):
        for symbol in symbols:
            rhs = grammar_dict.get(symbol, None)
            if rhs is None:
                yield symbol
            else:
                if isinstance(rhs, list):
                    rhs = ''.join(data for data in _decoder(rhs))
                    grammar_dict[symbol] = rhs
                yield rhs
    grammar_dict = decode_grammar(istream)
    for data in _decoder(grammar_dict[0]):
        ostream.write(data)
    ostream.flush()

# ______________________________________________________________________

def main(*args):
    opts, args = getopt.getopt(args, "cdh")
    stdout = False
    encoding = True
    for opt in opts:
        key, val = opt
        if key == '-c':
            stdout = True
        elif key == '-d':
            encoding = False
        elif key == "-h":
            print(USAGE)
    if encoding:
        for arg in args:
            with open(arg, 'rb') as in_file:
                if not stdout:
                    with open(arg + '.wot', 'wb') as out_file:
                        encode(in_file, out_file)
                else:
                    encode(in_file, sys.stdout)
    else:
        for arg in args:
            with open(arg, 'rb') as in_file:
                assert arg.endswith('.wot')
                if not stdout:
                    with open(arg[:-4], 'wb') as out_file:
                        decode(in_file, out_file)
                else:
                    decode(in_file, sys.stdout)

# ______________________________________________________________________

if __name__ == "__main__":
    main(*sys.argv[1:])
