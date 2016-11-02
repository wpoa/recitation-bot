#!/usr/bin/env python

import sqlite3, os
from pickle import dumps, loads

class SQLiteQueue(object):

	_sql_create = (
		'CREATE TABLE IF NOT EXISTS queue '
		'(id INTEGER PRIMARY KEY AUTOINCREMENT, item BLOB)'
	)
	_sql_size = 'SELECT COUNT(1) FROM queue'
	_sql_push = 'INSERT INTO queue (item) VALUES (?)'
	_sql_pop = 'SELECT id, item FROM queue ORDER BY id {direction} LIMIT 1'
	_sql_items = 'SELECT item FROM queue'
	_sql_del = 'DELETE FROM queue WHERE id = ?'

	def __init__(self, path, mode='FIFO'):
		self._path = os.path.abspath(path)
		self._db = sqlite3.Connection(self._path, timeout=60)
		self._db.text_factory = bytes
		self._sql_pop_formatted = self._sql_pop.format(direction = 'DESC' if mode == 'LIFO' else 'ASC')
		with self._db as conn:
			conn.execute(self._sql_create)

	def push(self, item):
		pickled_item = dumps(item)

		with self._db as conn:
			conn.execute(self._sql_push, (pickled_item,))

	def pop(self):
		with self._db as conn:
			for id_, item in conn.execute(self._sql_pop_formatted):
				conn.execute(self._sql_del, (id_,))
				return loads(item)

	def items(self):
		with self._db as conn:
			for item in conn.execute(self._sql_items):
				yield loads(item[0])

	def close(self):
		size = len(self)
		self._db.close()
		if not size:
			os.remove(self._path)

	def __len__(self):
		with self._db as conn:
			return next(conn.execute(self._sql_size))[0]

