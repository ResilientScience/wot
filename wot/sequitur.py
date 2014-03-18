"""SEQUITUR algorithm implementation in Python.

The SEQUITUR algorithm as developed by Craig Nevill-Manning and Ian Witten. They described implementation details in
their 1997 paper (http://www.jair.org/media/374/live-374-1630-jair.pdf) and included a Java implementation in the
on-line appendix of this paper. This is a reimplementation using Python. Therefore it tries to be pythonic whenver
 possible.

"SEQUITUR is an algorithm that infers a hierarchical structure from a sequence of discrete symbols by replacing
repeated phrases with a grammatical rule that generates the phrase, and continuing this process recursively. The result
is a hierarchical representation of the original sequence, which offers insights into its lexical structure. The
algorithm is driven by two constraints that reduce the size of the grammar, and produce structure as a by-product."

Notable changes:
- switched to md5sum for the hashtable
- eliminated logic and bookkeeping that is superfluous in Python

Outstanding questions:
- What exact output do we want from Sequitur? There are a couple valid possibilities. We could strictly tie ourselves to
the paper or use something a little more friendly. The syntax with S, or RX? This is important to figure out soon
because our tests need to validate whatever we choose.
"""

import sys


class Rule:
    """The represenation of a rule of the CFG."""
    def __init__(self, rulecount):
        self.guard = Guard(self)
        self.count = 0
        self.number = rulecount
        self.index = 0

    def first(self):
        return self.guard.n

    def last(self):
        return self.guard.p

    def get_rules(self):
        rules = []
        processed_rules = 0
        text = "Usage\tRule\n"
        rules.append(self)
        while processed_rules < len(rules):
            current_rule = rules[processed_rules]
            text += " %d\tR%d -> " % (current_rule.count, processed_rules)
            sym = current_rule.first()
            while not isinstance(sym, Guard):
                if isinstance(sym, NonTerminal):
                    refered_to = sym.r
                    if len(rules) > refered_to.index and rules[refered_to.index] == refered_to:
                        index = refered_to.index
                    else:
                        index = len(rules)
                        refered_to.index = index
                        rules.append(refered_to)
                    text += "R%d" % index
                else:
                    if sym.value == ' ':
                        text += '_'
                    elif sym.value == '\n':
                        text += '\\n'
                    else:
                        text += str(sym.value)
                text += ' '
                sym = sym.n
            text += '\n'
            processed_rules += 1
        return text


digrams = {}


class Symbol:
    def __init__(self):
        self.value = 0
        self.p = None
        self.n = None
        self.r = None
        global digrams

    def clone(self):
        sym = Symbol()
        sym.value = self.value
        sym.n = self.n
        sym.p = self.p
        return sym

    @staticmethod
    def join(left, right):
        """Joins two symbols, removing old diagrams from the dictionary."""
        if left.n is not None:
            left.delete_digram()
            # This code is ugly and handles a corner case, can it be made more elegant?
            if right.p is not None and right.n is not None and right.value == right.p.value and \
               right.value == right.n.value:
                digrams[str(right.value) + str(right.n.value)] = right
            if left.p is not None and left.n is not None and left.value == left.p.value and \
               left.value == left.n.value:
                digrams[str(left.p.value) + str(left.value)] = left.p
        left.n = right
        right.p = left

    def cleanup(self):
        """Abstract method that cleans up for symbol deletion."""
        pass

    def insert_after(self, to_insert):
        """Inserts a symbol after this one."""
        self.join(to_insert, self.n)
        self.join(self, to_insert)

    def delete_digram(self):
        """Removes the digram from the hash table."""
        try:
            if digrams[self.digram()] == self:
                digrams.pop(self.digram())
        except KeyError:
            pass

    def check(self):
        """Checks a new digram to figure out what to do with it.

        If it appears elsewhere, deals with it by calling match(), otherwise
        inserts it into the hash table.
        """
        if isinstance(self.n, Guard):
            return False
        if self.digram() not in digrams:
            digrams[self.digram()] = self
            return False
        found = digrams[self.digram()]
        if found.n != self:
            self.match(self, found)
        return True

    def substitute(self, r):
        """Replace a digram with a non-terminal."""
        self.cleanup()
        self.n.cleanup()
        self.p.insert_after(NonTerminal(r))
        if not self.p.check():
            self.p.n.check()

    @staticmethod
    def match(digram, matching):
        """Figure out what to do with a matching digram."""        
        global num_rules
        if isinstance(matching.p, Guard) and isinstance(matching.n.n, Guard):
            r = matching.p.r
            digram.substitute(r)
        else:
            r = Rule(num_rules)
            num_rules += 1
            first = digram.clone()
            second = digram.n.clone()
            r.guard.n = first
            first.p = r.guard
            first.n = second
            second.p = first
            second.n = r.guard
            r.guard.p = second
            matching.substitute(r)
            digram.substitute(r)
            digrams[str(first.value)+str(first.n.value)] = first
        if isinstance(r.first(), NonTerminal) and r.first().r.count == 1:
            r.first().expand()

    def expand(self):
        """We've hit a symbol that is the last reference to its rule. Substitute the rule in its place."""
        self.join(self.p, self.r.first())
        self.join(self.r.last(), self.n)
        digrams[str(self.r.last().value) + str(self.r.last().n.value)] = self.r.last()
        self.r.guard.r = None
        self.r.guard = None

    def digram(self):
        return str(self.value) + str(self.n.value)

    def equals(self, obj):
        return self.digram() == obj.digram()


class Terminal(Symbol):
    def __init__(self, value):
        Symbol.__init__(self)
        self.value = value

    def clone(self):
        sym = Terminal(self.value)
        sym.p = self.p
        sym.n = self.n
        return sym

    def cleanup(self):
        self.join(self.p, self.n)
        self.delete_digram()


class NonTerminal(Symbol):
    def __init__(self, rule):
        Symbol.__init__(self)
        self.r = rule
        self.r.count += 1
        self.value = self.r.number

    def clone(self):
        """Extra cloning method necessary so that count in the corresponding
        rule is increased.
        """
        sym = NonTerminal(self.r)
        sym.p = self.p
        sym.n = self.n
        return sym

    def cleanup(self):
        self.join(self.p, self.n)
        self.delete_digram()
        self.r.count -= 1


class Guard(Symbol):
    def __init__(self, rule):
        Symbol.__init__(self)
        self.r = rule
        self.p = self
        self.n = self

    def cleanup(self):
        self.join(self.p, self.n)


num_rules = 0


def run(text):
    global num_rules
    global digrams

    first_rule = Rule(num_rules)
    num_rules += 1
    digrams = {}
    for c in text:
        first_rule.last().insert_after(Terminal(c))
        first_rule.last().p.check()

    return first_rule.get_rules()


def main():
    """Open the file given as the first argument and print the CFG for it."""
    print run(open(sys.argv[1]).read())


if __name__ == "__main__":
    main()
