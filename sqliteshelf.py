#!/usr/bin/env python

import sqlite3, os
from pickle import dumps, loads

class SQLiteShelf:

	_sql_create = (
		'CREATE TABLE IF NOT EXISTS mapping '
		'(key BLOB PRIMARY KEY, value BLOB)'
	)
	_sql_size = 'SELECT COUNT(1) FROM mapping'
	_sql_set = 'INSERT OR REPLACE INTO mapping (key, value) VALUES (?, ?)'
	_sql_get = 'SELECT value FROM mapping WHERE key = (?) LIMIT 1'
	_sql_del = 'DELETE FROM mapping WHERE key = (?)'
	_sql_keys = 'SELECT key FROM mapping'

	def __init__(self, path):
		self._path = os.path.abspath(path)
		self._db = sqlite3.Connection(self._path, timeout=60)
		self._db.text_factory = bytes
		with self._db as conn:
			conn.execute(self._sql_create)

	def set(self, key, value):
		pickled_key = dumps(key)
		pickled_value = dumps(value)

		with self._db as conn:
			conn.execute(self._sql_set, (pickled_key, pickled_value,))

	def get(self, key):
		pickled_key = dumps(key)
		with self._db as conn:
			for value in conn.execute(self._sql_get, (pickled_key,)):
				return loads(value[0])
		# if we reach here, the entry was not found
		raise KeyError

	def __delitem__(self, key):
		pickled_key = dumps(key)
		with self._db as conn:
			conn.execute(self._sql_del, (pickled_key,))

	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, value):
		self.set(key, value)

	def keys(self):
		with self._db as conn:
			for key in conn.execute(self._sql_keys):
				yield loads(key[0])

	def close(self):
		size = len(self)
		self._db.close()
		#if not size: # nah
		#	os.remove(self._path)

	def __len__(self):
		with self._db as conn:
			return next(conn.execute(self._sql_size))[0]

