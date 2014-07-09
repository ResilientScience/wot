from wot import dimer


def setup():
    print("SETUP!")
        

def teardown():
    print("TEAR DOWN!")
    

def test_basic():
    print("I RAN!")


def test_input1():
    assert dimer.histogram("tests/data/FILE1", 2) == open("tests/data/FILE1.2").read()
    
def test_input2():
    assert dimer.histogram("tests/data/FILE2", 2) == open("tests/data/FILE2.2").read()
    
def test_input3():
    assert dimer.histogram("tests/data/FILE3", 2) == open("tests/data/FILE3.2").read()
    
def test_input4():
    assert dimer.histogram("tests/data/FILE4", 2) == open("tests/data/FILE4.2").read()
