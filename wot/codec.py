#! /usr/bin/env python
# ______________________________________________________________________
# requires bitarray: pip install bitarray

from wot import mrwot
from collections import Counter
import sys, struct, bitarray, getopt
import StringIO # PY2

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

def encode_grammar_dict(coding, rules):
    grammar_dict = {}
    rhs = bitarray.bitarray()
    for rule in rules:
        if rule is not None:
            del rhs[:]
            _, rhs_symbols = rule.dump()
            rhs.encode(coding, rhs_symbols)
            symbol_nr = rule.number
            rhs_bytes = rhs.tobytes()
            grammar_dict[symbol_nr] = len(rhs_symbols), rhs_bytes
    return grammar_dict

# ______________________________________________________________________

def preprocess_grammar(grammar):
    """Given a grammar, compute a symbol histogram map, use that to
    create a prefix coding, then output the histogram, and a map from
    nonterminal symbols to coded right-hand-sides.
    """
    hist = unigram(grammar)
    tree = build_tree2(hist)
    code = build_prefix_code_map(tree)
    grammar_dict = encode_grammar_dict(code, grammar.rules)
    return hist, grammar_dict

# ______________________________________________________________________

def encoder_outputs(hist, grammar_dict):
    keys = grammar_dict.keys()
    keys.sort()
    max_symbol = max(keys)
    yield "WOT\x00"
    yield max_symbol
    for byte_val in xrange(256):
        yield hist[chr(byte_val)]
    for sym_nr in xrange(max_symbol + 1):
        yield hist[sym_nr]
    # XXX Remove this?  Can compute this value from the number of
    # empty nonterminals.
    offset_count = len(keys) - 1
    yield offset_count
    for symbol_nr in keys[:-1]:
        yield len(grammar_dict[symbol_nr][1])
    for symbol_nr in keys:
        yield grammar_dict[symbol_nr][0]
        yield grammar_dict[symbol_nr][1]
    yield ''

# ______________________________________________________________________

def encode_grammar(grammar):
    """Returns generator that outputs a compressed representation of
    the input grammar.
    """
    hist, grammar_dict = preprocess_grammar(grammar)
    return encoder_outputs(hist, grammar_dict)

# ______________________________________________________________________

def process_decode_stream(istream):
    """Return a generator that yields values similar to those
    generated by encode_grammar(), but as part of the decoding process.
    """
    def _getint():
        return single_int.unpack(istream.read(4))[0]
    single_int = struct.Struct("<I")
    yield istream.read(4)
    max_symbol = _getint()
    yield max_symbol
    for _ in xrange(256):
        yield _getint()
    symbols = 1
    for _ in xrange(max_symbol + 1):
        count = _getint()
        if count > 0:
            symbols += 1
        yield count
    offset_count = _getint()
    assert offset_count == symbols - 1
    yield offset_count
    offsets = []
    for _ in xrange(offset_count):
        offset = _getint()
        offsets.append(offset)
        yield offset
    for coded_rule_len in offsets:
        yield _getint()
        yield istream.read(coded_rule_len)
    yield _getint()
    yield istream.read()
    yield ''

# ______________________________________________________________________

def decode_grammar_dict(istream):
    """Given a stream (file or file-like object), return a dictionary
    of the grammar rules (mapping from nonterminals to mixed lists of
    terminals and nonterminals).
    """
    hist = Counter()
    ingen = process_decode_stream(istream)
    assert next(ingen) == "WOT\x00"
    max_symbol = next(ingen)
    for byte_val in xrange(256):
        count = next(ingen)
        if count > 0:
            hist[chr(byte_val)] = count
    symbols = [0]
    for sym_nr in xrange(max_symbol + 1):
        count = next(ingen)
        if count > 0:
            hist[sym_nr] = count
            symbols.append(sym_nr)
    offset_count = next(ingen)
    offset_symbols = symbols[:-1]
    assert offset_count == len(offset_symbols), (
        "%d != %d!" % (offset_count, len(offset_symbols)))
    for _ in offset_symbols:
        next(ingen)
    tree = build_tree2(hist)
    code = build_prefix_code_map(tree)
    grammar_dict = {}
    ba = bitarray.bitarray()
    for sym_nr in offset_symbols:
        sym_count = next(ingen)
        sym_str = next(ingen)
        ba.frombytes(sym_str)
        grammar_dict[sym_nr] = ba.decode(code)[:sym_count]
        del ba[:]
    sym_count = next(ingen)
    sym_str = next(ingen)
    ba.frombytes(sym_str)
    grammar_dict[symbols[-1]] = ba.decode(code)[:sym_count]
    assert next(ingen) == ''
    return grammar_dict

# ______________________________________________________________________

def encode(istream, ostream):
    grammar = mrwot.Grammar()
    input_buf = istream.read(SIXTY4K)
    while len(input_buf) > 0:
        grammar.build(input_buf)
        input_buf = istream.read(SIXTY4K)
    single_int = struct.Struct("<I")
    for out_elem in encode_grammar(grammar):
        if isinstance(out_elem, int):
            out_elem = single_int.pack(out_elem)
        ostream.write(out_elem)
    ostream.flush()

# ______________________________________________________________________

def encode_str(instr):
    grammar = mrwot.Grammar()
    grammar.build(instr)
    single_int = struct.Struct("<I")
    return "".join(single_int.pack(out_elem) if isinstance(out_elem, int)
                   else out_elem for out_elem in encode_grammar(grammar))

# ______________________________________________________________________

def decode(istream, ostream):
    def _decoder(symbols):
        symbols.reverse()
        while len(symbols) > 0:
            symbol = symbols.pop()
            if symbol not in grammar_dict:
                yield symbol
            elif symbol in grammar_memo:
                yield grammar_memo[symbol]
            else:
                rhs = grammar_dict[symbol][:]
                rhs.reverse()
                symbols.extend(rhs)
    grammar_dict = decode_grammar_dict(istream)
    grammar_memo = dict((item[0], ''.join(item[1]))
                        for item in grammar_dict.items()
                        if all(sym not in grammar_dict for sym in item[1]))
    for data in _decoder(grammar_dict[0]):
        ostream.write(data)
    ostream.flush()

# ______________________________________________________________________

def test_generators():
    grm = mrwot.Grammar()
    grm.build(USAGE)
    enc_list = list(encode_grammar(grm))
    single_int = struct.Struct("<I")
    enc_str = "".join(single_int.pack(out_elem) if isinstance(out_elem, int)
                      else out_elem for out_elem in enc_list)
    decode_stream = StringIO.StringIO(enc_str)
    dec_list = list(process_decode_stream(decode_stream))
    decode_stream.close()
    assert enc_list == dec_list, "%r != %r!" % (enc_list, dec_list)
    return grm, enc_list, enc_str

# ______________________________________________________________________

def test_grammar_dicts():
    grm = mrwot.Grammar()
    grm.build(USAGE)
    grm_dict = grm.rules_to_dict()
    hist, enc_grm_dict = preprocess_grammar(grm)
    assert enc_grm_dict.keys() == grm_dict.keys()
    single_int = struct.Struct("<I")
    enc_str = "".join(single_int.pack(out_elem) if isinstance(out_elem, int)
                      else out_elem 
                      for out_elem in encoder_outputs(hist, enc_grm_dict))
    decode_stream = StringIO.StringIO(enc_str)
    dec_grm_dict = decode_grammar_dict(decode_stream)
    decode_stream.close()
    assert enc_grm_dict.keys() == dec_grm_dict.keys()
    for key in grm_dict.keys():
        grm_rhs = list(grm_dict[key])
        dec_rhs = dec_grm_dict[key]
        assert grm_rhs == dec_rhs, (
            "grm_dict[%r] != dec_grm_dict[%r] (%r != %r)!" % (
                key, key, grm_rhs, dec_rhs))
    return enc_grm_dict, dec_grm_dict

# ______________________________________________________________________

def test_codec():
    inp0 = StringIO.StringIO(USAGE)
    out0 = StringIO.StringIO()
    encode(inp0, out0)
    inp0.close()
    inp1 = StringIO.StringIO(out0.getvalue())
    out0.close()
    out1 = StringIO.StringIO()
    decode(inp1, out1)
    inp1.close()
    result = out1.getvalue()
    assert USAGE == result, "%r != %r!" % (USAGE, result)
    out1.close()

# ______________________________________________________________________

def test():
    test_generators()
    test_grammar_dicts()
    test_codec()

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
