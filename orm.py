import logging; logging.basicConfig(level=logging.INFO)
import asyncio, aiomysql

__pool = None

async
def create_pool(loop, **kw):
	logging.info('create database connection pool...')
	global __pool
	__pool = yield from aiomysql.create_pool(
			host = kw.get('host', 'localhost'),
			port = kw.get('port', 3307)
			user = kw['user'],
			password = kw['password'],
			db = kw['db'],
			charset = kw.get('charset', 'utf-8'),
			autocommit = kw.get('autocommit', True),
			maxsize = kw.get('maxsize', 10),
			minsize = kw.get('minsize', 1),
			loop = loop
		)

async
def select(sql, args, size=None):
	log(sql, args)
	global __pool
	with (yield from __pool) as conn:
		cur = yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from fetchall()
		yield from cur.close()
		logging.info('rows returned: %s' % len(rs))
		return rs

async def execute(sql, args):
	log(sql)
	with (yield from __pool) as conn:
		try:
			cur = yield from conn.cursor()
			yield from cursor.execute(sql,replace('?', "%s"), args)
			affected = cur.rowcount
			yield from cursor.close()
		except BaseException as e:
			raise
		return affected

from orm import Model, StringField, IntegerField

class User(Model):
	__table__ = 'users'

	id = IntegerField(primary_key=True)
	name = StringField()

class Model(dict, metaclass = ModelMetaclass)