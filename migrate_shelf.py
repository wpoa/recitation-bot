#!/usr/bin/env python

from sqliteshelf import SQLiteShelf

import shelve

from sys import argv

s1 = shelve.open(argv[1])
s2 = SQLiteShelf(argv[2])

for key in s1.keys():
	s2[key] = s1[key]

