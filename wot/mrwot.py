from mrjob.job import MRJob, JSONProtocol

# ______________________________________________________________________

TERMINAL_CLASSES = bytes, unicode if bytes == str else str

class Symbol(object):
    __slots__ = ('grammar', 'next', 'prev', 'terminal', 'rule')

    def __init__(self, grammar, value):
        self.grammar = grammar
        self.next = None
        self.prev = None
        self.terminal = None
        self.rule = None
        if isinstance(value, TERMINAL_CLASSES):
            self.terminal = value
        elif isinstance(value, Symbol):
            if value.terminal:
                self.terminal = value.terminal
            else:
                assert value.rule is not None
                self.rule = value.rule
                self.rule.reference_count += 1
        elif isinstance(value, Rule):
            self.rule = value
            self.rule.reference_count += 1
        else:
            raise ValueError("Don't know how to handle symbol value %r" %
                             (value,))

    def check(self):
        ret_val = True
        if self.is_guard() or self.next.is_guard():
            ret_val = False
        else:
            key = self.hash_value()
            match = self.grammar.digram_map.get(key)
            if match is None:
                self.grammar.digram_map[key] = self
                ret_val = False
            else:
                if match.next != self:
                    self.process_match(match)
        return ret_val

    def delete(self):
        self.prev.join(self.next)
        if not self.is_guard():
            self.delete_digram()
            if self.rule:
                self.rule.reference_count -= 1

    def delete_digram(self):
        if not (self.is_guard() or self.next.is_guard()):
            hash_value = self.hash_value()
            if self.grammar.digram_map.get(hash_value) == self:
                del self.grammar.digram_map[hash_value]

    def dump(self):
        return self.terminal if self.terminal is not None else self.rule.number

    def expand(self):
        assert self.rule is not None
        left = self.prev
        right = self.next
        first = self.rule.first()
        last = self.rule.last()
        key = self.hash_value()
        if self.grammar.digram_map.get(key) is self:
            del self.grammar.digram_map[key]
        left.join(first)
        last.join(right)
        self.grammar.digram_map[last.hash_value()] = last

    def hash_value(self):
        return (self.dump(), self.next.dump())

    def insert_after(self, symbol):
        symbol.join(self.next)
        self.join(symbol)

    def is_guard(self):
        return (self.rule is not None) and (self.rule.guard == self)

    def is_tripple(self):
        value = self.value()
        return ((self.prev is not None) and (self.next is not None) and 
                (value == self.prev.value()) and (value == self.next.value()))

    def join(self, right):
        if self.next is not None:
            self.delete_digram()
            if right.is_tripple():
                self.grammar.digram_map[right.hash_value()] = right
            if self.is_tripple():
                self.grammar.digram_map[self.hash_value()] = self
        self.next = right
        right.prev = self

    def process_match(self, match):
        match_prev = match.prev
        if match_prev.is_guard() and match.next.next.is_guard():
            rule = match.prev.rule
            assert rule is not None
            self.substitute(rule)
        else:
            rule = self.grammar.add_rule()
            rule.last().insert_after(self.grammar.add_symbol(self))
            rule.last().insert_after(self.grammar.add_symbol(self.next))
            match.substitute(rule)
            self.substitute(rule)
            first = rule.first()
            self.grammar.digram_map[first.hash_value()] = first
        first = rule.first()
        first_rule = first.rule
        if (first_rule is not None) and (first_rule.reference_count == 1):
            first.expand()
            self.grammar.remove_rule(first_rule)

    def substitute(self, rule):
        prev = self.prev
        prev.next.delete()
        prev.next.delete()
        prev.insert_after(self.grammar.add_symbol(rule))
        if not prev.check():
            prev.next.check()

    def value(self):
        return self.terminal if self.terminal is not None else self.rule

# ______________________________________________________________________

class Rule(object):
    __slots__ = ('grammar', 'guard', 'reference_count', 'number')

    def __init__(self, grammar):
        self.grammar = grammar
        self.reference_count = 0
        self.guard = grammar.add_symbol(self)
        self.guard.join(self.guard)
        self.reference_count -= 1 # Remove guard from reference count.
        assert self.reference_count == 0
        self.number = len(grammar.rules)

    def dump(self):
        return self.number, self.symbols()

    def first(self):
        return self.guard.next

    def iter_symbols(self):
        crnt = self.guard.next
        while not crnt.is_guard():
            yield crnt
            crnt = crnt.next

    def last(self):
        return self.guard.prev

    def symbols(self):
        return tuple(symbol.dump() for symbol in self.iter_symbols())

# ______________________________________________________________________

class Grammar(object):
    def __init__(self):
        self.digram_map = {}
        self.rules = []
        self.root = self.add_rule()
        self.segment = None

    def add_rule(self):
        ret_val = Rule(self)
        self.rules.append(ret_val)
        return ret_val

    def add_symbol(self, value):
        return Symbol(self, value)

    def remove_rule(self, rule):
        assert rule in self.rules
        idx = self.rules.index(rule)
        self.rules[idx] = None
        rule.grammar = None

    def build(self, sequence, segment=None):
        self.segment = segment
        for elem in sequence:
            self.root.last().insert_after(self.add_symbol(elem))
            self.root.last().prev.check()

    def dump(self):
        return self.segment, tuple(rule.dump() for rule in self.rules
                                   if rule is not None)

    def join(self, other_grammar):
        assert ((self.segment is None) or
                (self.segment != other_grammar.segment))
        common_rule_mapping = self.map_common_rules(other_grammar)
        # Like in load(), first build empty rules, but also build a
        # complete renumbering map.
        final_rule_mapping = common_rule_mapping.copy()
        other_rules_for_insertion = [
            other_rule 
            for other_rule in other_grammar.rules 
            if not common_rule_mapping.has_key(other_rule.number)]
        for other_rule in other_rules_for_insertion:
            new_rule = self.add_rule()
            final_rule_mapping[other_rule.number] = new_rule.number
        # Now with a complete mapping from one grammar to another, we
        # can insert symbols into the new rules.
        my_rule_map = dict((rule.number, rule) for rule in self.rules)
        for other_rule in other_rules_for_insertion:
            new_rule = my_rule_map[final_rule_mapping[other_rule.number]]
            insertion_point = new_rule.guard
            for other_symbol in other_rule.iter_symbols():
                other_value = other_symbol.value()
                if isinstance(other_value, Rule):
                    my_value = my_rule_map[
                        final_rule_mapping[other_value.number]]
                else:
                    # This is a terminal
                    my_value = other_value
                insertion_point.insert_after(self.add_symbol(my_value))
                # XXX This might be risky while we are just trying to
                # dump the other grammar into this one.  Maybe
                # implement a Grammar.recheck() method?
                insertion_point.check()
                insertion_point = insertion_point.next
        return my_rule_map[final_rule_mapping[other_grammar.root.number]]

    @classmethod
    def load(cls, payload, *args, **kws):
        segment, rules = payload
        ret_val = cls(*args, **kws)
        ret_val.segment = segment
        rule_map = {}
        for rule_data in rules:
            rule_no, _ = rule_data
            if rule_no != 0:
                rule = ret_val.add_rule()
                rule.number = rule_no
            else:
                rule = ret_val.root
            rule_map[rule_no] = rule
        for rule_data in rules:
            rule_no, rule_seq = rule_data
            rule = rule_map[rule_no]
            for elem in rule_seq:
                elem = rule_map.get(elem, elem)
                rule.last().insert_after(ret_val.add_symbol(elem))
                rule.last().prev.check() # updates digram map
        return ret_val

    def map_common_rules(self, other_grammar):
        ret_val = {}
        # __________________________________________________
        def is_only_terminals(symbols):
            return int not in (type(symbol) for symbol in symbols)
        # __________________________________________________
        def is_fully_rewritable(symbols):
            nonterminal_set = set(symbol for symbol in symbols
                                  if type(symbol) == int)
            intersected_set = nonterminal_set.intersection(ret_val.keys())
            return nonterminal_set == intersected_set
        # __________________________________________________
        def handle_common_vectors(my_vector_set, other_vector_set,
                                  other_vector_map):
            common_vectors = my_vector_set.intersection(other_vector_set)
            for common_vector in common_vectors:
                my_rule_number = my_rule_vec_map[common_vector]
                other_rule_number = other_vector_map[common_vector]
                ret_val[other_rule_number] = my_rule_number
                my_vector_set.remove(common_vector)
            return len(common_vectors) > 0
        # __________________________________________________
        my_rule_vec_map = dict((rule.symbols(), rule.number)
                               for rule in self.rules)
        my_rule_vector_set = set(my_rule_vec_map.keys())
        other_rule_vec_map = dict((other_rule.symbols(), other_rule.number)
                                  for other_rule in other_grammar.rules)
        my_terminal_only_rule_vectors = set(
            my_vector
            for my_vector in my_rule_vector_set
            if is_only_terminals(my_vector))
        other_terminal_only_rule_vectors = set(
            other_rule_symbols
            for other_rule_symbols in other_rule_vec_map.keys()
            if is_only_terminals(other_rule_symbols))
        changed = handle_common_vectors(my_terminal_only_rule_vectors,
                                        other_terminal_only_rule_vectors,
                                        other_rule_vec_map)
        if changed:
            # Remove terminal only vectors from future consideration...
            my_rule_vector_set = my_rule_vector_set.difference(
                my_terminal_only_rule_vectors)
            for other_vector in other_terminal_only_rule_vectors:
                del other_rule_vec_map[other_vector]
        while changed:
            other_rule_vector_set = set()
            other_rule_rewrite_map = {} # Map rewritten vectors to
                                        # other grammar's rule number.
            for other_rule_key_value in other_rule_vec_map.items():
                other_rule_vector, other_rule_number = other_rule_key_value
                if is_fully_rewritable(other_rule_vector):
                    rewrite_vec = tuple(
                        ret_val.get(other_rule_symbol, other_rule_symbol)
                        for other_rule_symbol in other_rule_vector)
                    other_rule_vector_set.add(rewrite_vec)
                    other_rule_rewrite_map[rewrite_vec] = other_rule_number
            changed = handle_common_vectors(my_rule_vector_set,
                                            other_rule_vector_set,
                                            other_rule_rewrite_map)
        return ret_val

# ______________________________________________________________________

class MRWoT(MRJob):
    INPUT_PROTOCOL = JSONProtocol

    def mapper(self, key, value):
        grammar = Grammar()
        grammar.build(value, key)
        yield None, grammar.dump()

    def reducer(self, key, values):
        segments = {}
        result = None
        grammar = None
        try:
            grammar_data = next(values)
            grammar = Grammar.load(grammar_data)
            segments[grammar.segment] = grammar.root.number
        except StopIteration:
            pass
        for grammar_data in values:
            next_grammar = Grammar.load(grammar_data)
            joined_root = grammar.join(next_grammar)
            segments[next_grammar.segment] = joined_root.number
        if grammar is not None:
            _, rules = grammar.dump()
            result = rules
        yield key, (segments.items(), result)

# ______________________________________________________________________

if __name__ == "__main__":
    MRWoT.run()
