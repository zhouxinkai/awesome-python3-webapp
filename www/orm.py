#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from logger import logger

import asyncio, aiomysql

import pdb

__pool = None

def log(sql, args=()):
    logger.info('SQL: %s' % sql)

async def create_pool(loop, **kw):
	# 负责创建一个全局的数据连接对象
	logger.info('create database connection pool...')
	global __pool
	__pool = await aiomysql.create_pool(
	        host=kw.get('host', 'localhost'),
	        port=kw.get('port', 3306),
	        user=kw['user'],
	        password=kw['password'],
	        db=kw['database'],
	        charset=kw.get('charset', 'utf8'),
	        autocommit=kw.get('autocommit', True),
	        maxsize=kw.get('maxsize', 10),
	        minsize=kw.get('minsize', 1),
	        loop = loop
		)

async def select(sql, args, size=None):
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
            	# 取得所有行的数据，作为列表返回，一行数据是一个字典
        logger.info('rows returned: %s' % len(rs))
        return rs

async def execute(sql, args, autocommit=True):
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if autocommit:
                await conn.commit()
                logger.info('commit success!')
        except BaseException as e:
            if not autocommit:
                await conn.rollback()
            raise
        return affected

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)

class Field(object):
	# 用于描述表中的一列
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
	def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
		super().__init__(name, ddl, primary_key, default)		

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

class ModelMetaclass(type):

	def __new__(cls, name, bases, attrs):
		# 排除Model类本身
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
		# 获取table名称
		tableName = attrs.get('__table__', None) or name
		logger.info('found model: %s (table: %s)' % (name, tableName))
		# 获取所有的Field和主键名
		mappings = dict()
		fields = []
		primaryKey = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				logger.info('found mapping: %s ==> %s' % (k,v))
				mappings[k] = v;
				if v.primary_key:
					#找到主键
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field: %s' %k)
					primaryKey = k
				else:
					fields.append(k)

		if not primaryKey:
			raise RuntimeError('Primary key not found')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))
		attrs['__mappings__'] = mappings  # 保存类属性和列的映射关系
		attrs['__table__'] = tableName
		attrs['__primary_key__'] = primaryKey # 主键属性名
		attrs['__fields__'] = fields 	# 除主键外的属性名
		# 构造默认的SELECT、INSERT、UPDATE和DELETE语句
		attrs['__select__'] =  'select `%s`, %s from `%s`' % (primaryKey, ','.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ','.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set %s where `%s` = ?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		attrs['__delete__'] = 'delete from `%s` where `%s` = ?' % (tableName, primaryKey)
		return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass = ModelMetaclass):
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)

	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'" % key)

	def __setattr__(self, key, value):
		self[key] = value

	def getValue(self, key):
		return getattr(self, key, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)  # 会去调用__getattr__
		if value is None:		# x is y ,用于判断x和y是不是同一个对象， is称为同一性运算符
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				logger.info("useing default value for %s: %s" % (key, str(value)))
				setattr(self, key, value) # 会去调用__setattr__
		return value	

	@classmethod
	async def findAll(cls, where=None, args=None, **kw):
	    ' find objects by where clause. '
	    sql = [cls.__select__]
	    if where:
	        sql.append('where')
	        sql.append(where)
	    if args is None:
	        args = []
	    orderBy = kw.get('orderBy', None)
	    if orderBy:
	        sql.append('order by')
	        sql.append(orderBy)
	    limit = kw.get('limit', None)
	    if limit is not None:
	        sql.append('limit')
	        if isinstance(limit, int):
	            sql.append('?')
	            args.append(limit)
	        elif isinstance(limit, tuple) and len(limit) == 2:
	            sql.append('?, ?')
	            args.extend(limit)
	        else:
	            raise ValueError('Invalid limit value: %s' % str(limit))
	    rs = await select(' '.join(sql), args)
	    return [cls(**r) for r in rs]

	@classmethod
	async def findNumber(cls, selectField, where=None, args=None): # 获取行数
	    ' find number by select and where. '
	    sql = ['select %s as `_num_` from `%s`' % (selectField, cls.__table__)]
	    # 这里的 _num_ 为别名，任何客户端都可以按照这个名称引用这个列，就像它是个实际的列一样
	    if where:
	        sql.append('where')
	        sql.append(where)
	    rs = await select(' '.join(sql), args, 1) #  size = 1, 表示只取一行数据
	    if len(rs) == 0:
	        return None
	    return rs[0].get('_num_', None)
	    # rs[0]表示一行数据,是一个字典，而rs是一个列表

	@classmethod
	@asyncio.coroutine
	def find(cls, pk):
		# classmethod表示参数cls被绑定到类的类型对象(在这里即为<class '__main__.User'> )，
		# 而不是实例对象
		'find object by primary key.'
		rs = yield from select('%s where `%s` = ?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])
		# 1.将rs[0]转换成关键字参数元组，rs[0]为dict
		# 2.通过<class '__main__.User'>(位置参数元组)，产生一个实例对象

	@asyncio.coroutine
	def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__)) # args表示要插入的数据
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = yield from execute(self.__insert__, args)
		if rows != 1:
			logger.info('failed to insert record: affected rows : %s' % rows)

	async def update(self):
	    args = list(map(self.getValue, self.__fields__))
	    args.append(self.getValue(self.__primary_key__))
	    rows = await execute(self.__update__, args)
	    if rows != 1:
	        logger.info('failed to update by primary key: affected rows: %s' % rows)

	async def remove(self):
	    args = [self.getValue(self.__primary_key__)]
	    rows = await execute(self.__delete__, args)
	    if rows != 1:
	        logger.info('failed to remove by primary key: affected rows: %s' % rows)

'''#test code
class User(Model):
	__table__ = 'users'

	id = IntegerField(primary_key=True)
	name = StringField()
    def __init__(self, **kw):
        super(User, self).__init__(**kw)

u = User(id=12345, name='Michael')
#instance(u, dict)=True,u是一个字典
u.save()'''