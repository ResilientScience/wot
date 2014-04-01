from wot import sequitur


def setup():
    print("SETUP!")
        

def teardown():
    print("TEAR DOWN!")
    

def test_basic():
    print("I RAN!")


def test_input1():
    assert sequitur.run('abracadabraabracadabra') == \
        'Usage\tRule\n 0\tR0 -> R1 R1 \n 2\tR1 -> R2 c a d R2 \n 2\tR2 -> a b r a \n'


def test_input2():
    assert sequitur.run('11111211111') == 'Usage\tRule\n 0\tR0 -> R1 R2 2 R2 R1 \n 3\tR1 -> 1 1 \n 2\tR2 -> R1 1 \n'


def test_input3():
    assert sequitur.run(open("tests/data/69k").read()) == open("tests/data/69k.out").read()
