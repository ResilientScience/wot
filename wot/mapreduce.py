"""MapReduce implementation of the Sequitur algorithm.

Right now this is really just using mapreduce as a way of scalable batch processing. A true massively-parallel mapreduce
reimplementation could lead to some crazy good performance if done right. Sequitur is a recursive algorithm, but I think
Team Resilient could find a way.
"""

from mrjob.job import MRJob
import sequitur


class MRSequitur(MRJob):
    """The MRJob runner."""
    def mapper(self, _, line):
        output = sequitur.run(open(line).read())
        yield line, output
        

if __name__ == '__main__':
    MRSequitur.run()


