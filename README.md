# wot #

Web Of Trails (wot) is a fast and structural indexing system. This is a grammar-based approach to indexing data. It uses the Sequitur algorithm to produces a context-free grammar (CFG) of the data.

> "Our ineptitude in getting at the record is largely caused by the artificiality of systems of indexing. When data of any sort are placed in storage, they are filed alphabetically or numerically, and information is found (when it is) by tracing it down from subclass to subclass. It can be in only one place, unless duplicates are used; one has to have rules as to which path will locate it, and the rules are cumbersome. Having found one item, moreover, one has to emerge from the system and re-enter on a new path. The human mind does not work that way. It operates by association. With one item in its grasp, it snaps instantly to the next that is suggested by the association of thoughts, in accordance with some intricate **web of trails**" -- Vannevar Bush, As We May Think

## Motivation ##

wot provides a linear-space indexer designed to supplant polynomial-space indexers. This primary benefit could make it a game-changer for the deep web.

## Current status ##
This is currently being tested in the domain of comparative genomics, where many petabytes of data can be indexed to improve performance and advance fundamental science.

## Python 3 support ##
wot does not currently support Python 3, which is a shame given the direction of this project. The current dependencies do not yet support Python 3, but when they do we will enthusiastically support it.

 1. boto
 2. mrjob - mrjob shares boto as a dependency.
