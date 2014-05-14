#! /usr/bin/env python
# ______________________________________________________________________
# Module imports

import math
import sys
import timeit

from wot import codec

# ______________________________________________________________________
# Function definitions

def bench_codec(path, max_time=60., quiet=True):
    with open(path, 'rb') as file_obj:
        file_data = file_obj.read()
    file_len = len(file_data)
    test_lengths = [2 ** n
                    for n in xrange(3, int(math.log(file_len, 2)) + 1)]
    test_lengths.append(file_len)
    results = {}
    for test_length in test_lengths:
        test_data = file_data[:test_length]
        t0 = timeit.default_timer()
        encoded_str = codec.test_encode(test_data)
        t1 = timeit.default_timer()
        decoded_str = codec.test_decode(encoded_str)
        t2 = timeit.default_timer()
        assert test_data == decoded_str, '%r != %r' % (test_data, decoded_str)
        encoding_time = t1 - t0
        decoding_time = t2 - t1
        total_time = t2 - t0
        compression_ratio = float(len(encoded_str))/test_length
        result = (encoding_time, decoding_time, total_time, compression_ratio)
        results[test_length] = result
        if not quiet:
            print('%d: %r' % (test_length, result))
        if total_time >= max_time:
            break
    return results

# ______________________________________________________________________
# Main routine

def main(*args):
    for arg in args:
        print("_" * 70)
        print(arg)
        print("_" * 60)
        bench_codec(arg, quiet=False)

# ______________________________________________________________________

if __name__ == "__main__":
    main(*sys.argv[1:])
