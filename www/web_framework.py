import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import Web

from apis import APIError

# --------------get和post装饰器，用于增加__method__和__route__特殊属性，分别标记请求方法和请求路径

def get(path):
	'''Define decorator @get('/path')'''
	def decorator(func):
		@functools.wraps(func)
		# 本条语句是为了调试方便，可以忽略不看
		def wrapper(*args, **kw):
			return func(*args, **kw)
			# 执行func(*args, **kw)，并返回结果
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator
#decorator是一个装饰器，其必须使用函数func作为参数
#为了向装饰器传递参数，必须使用另外一个函数（在这里为get）来创建装饰器

def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			return func(*args, **kw)
		wrapper.__method__  = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator

# ---------------------------- 使用inspect模块中的signature方法来获取函数的参数，实现一些复用功能--
# 关于inspect.Parameter 的  kind 类型有5种：
# POSITIONAL_ONLY		只能是位置参数
# POSITIONAL_OR_KEYWORD	可以是位置参数也可以是关键字参数
# VAR_POSITIONAL			相当于是 *args
# KEYWORD_ONLY			关键字参数且提供了key
# VAR_KEYWORD			相当于是 **kw

def get_required_kw_args(fn):
	# 如果url处理函数需要传入关键字参数，且默认是空的话，获取这个key
	agrs = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			agrs.append(name)
	return tuple(agrs)
	# 返回函数的形参元组

def get_all_kw_agrs(fn):
	# 如果url处理函数需要传入关键字参数，获取这个key
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)
 
def has_kw_agr(fn):
	# 判断是否有关键字参数
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True

def has_var_kw_arg(fn):
	# 判断是否有关键字变长参数，VAR_KEYWORD对应**kw
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
	# 判断是否存在一个参数叫做request，并且该参数要在其他普通的位置参数之后
	sig = inspect.signature(fn)
	params = sig.parameters
	found = False
	for name, param in params.items():
		if name == 'request':
			found = True
			continue	
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			# 如果判断为True，则表明param只能是位置参数POSITIONAL_ONLY
			raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
	return found

# RequestHandler目的就是从URL处理函数（如handlers.index）中分析其需要接收的参数，从web.request对象中获取必要的参数，
# 调用URL处理函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：
class RequestHandler(object):
# RequestHandler是一个类，由于定义了__call__()方法，因此可以将其实例视为函数。
	def __init__(self, app, fn):
		self._app = app
		self._func = fn
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_kw_arg = has_kw_arg(fn)
		self._all_kw_args = get_all_kw_agrs(fn)
		self._required_kw_args = get_required_kw_args(fn)

	def __get_request_content(self):
		kw = None

		if self._has_var_kw_agr or self._has_kw_arg or self._required_kw_args:
		# 确保URL处理函数有参数	
			if request.methd == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content-Type')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = yield from request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('application/form-data'):
					params = yield from request.post()
					kw = dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)

			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
					# 解析url中?后面的键值对内容保存到kw
					'''qs = 'first=f,s&second=s'
					parse.parse_qs(qs, True).items()	
					>>> dict([('first', ['f,s']), ('second', ['s'])])
					'''
						kw[k] = v[0]
			return kw

	# __call__方法的代码逻辑:
	# 1.定义kw对象，用于保存参数
	# 2.判断URL处理函数是否存在参数，如果存在则根据是POST还是GET方法将request请求内容保存到kw
	# 3.如果kw为空(说明request没有请求内容)，则将match_info列表里面的资源映射表赋值给kw；如果不为空则把命名关键字参数的内容给kw
	# 4.完善_has_request_arg和_required_kw_args属性
	@asyncio.coroutine
	def __call__(self, request):
		kw = __get_request_content()

		if kw is None:
		# 参数为空说明没有从request对象中获取到参数
		'''def hello(request):
			    text = '<h1>hello, %s!</h1>' % request.match_info['name']
			    return web.Response() 
			app.router.add_route('GET', '/hello/{name}', hello)
	    '''
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_agr and self._all_kw_args:
				# not的优先级比and的优先级要高
				# remove all unamed kw， 从kw中删除URL处理函数中所有不需要的参数
				copy = dict()
				for name in self._all_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			# check named arg:
			for k, v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args %s' % k)
				kw[k] = v

		if self._has_request_arg:
		# 如果有request这个参数，则把request对象加入kw['request']	
			kw['request'] = request
		
		if self._required_kw_args:
		# check required kw,检查是否有必需关键字参数	
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBadRequest('Missing argument: %s' % name)

		# 以上代码均是为了获取调用参数
		logging.info('call with args: %s' % str(kw))

		try:
			r = yield from self._func(**kw)
			return r
		except APIError as e:
			return dict(error = e.error, data = e.data, message = e.message)


def add_route(app, fn):
	# URL处理函数
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.', % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
		#用asyncio.coroutine装饰函数fn
	logging.info('add route %s %s => %s(%s)', % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
	# 最后一个参数是形参列表
	app.router.add_route(method, path, RequestHandler(app, fn))
	# 正式注册为相应的url处理函数
    # 处理方法为RequestHandler的自省函数 '__call__'

def add_routes(app, module_name):
	# module_name格式 'handlers.index'
	n = module_name.rfind('.')
	if n == (-1):
		mod = __import__(module_name, globals(), locals())
		'''__import__ 作用同import语句，但__import__是一个函数，并且只接收字符串作为参数, 其实import语句就是调用这个函数进行导入工作的, 其返回值是对应导入模块的引用
		__import__('os',globals(),locals(),['path','pip']) ,等价于from os import path, pip'''
	else:
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		# dir函数的作用是列出对象的所有特性（以及模块的所有函数、类、变量等），见<<Python基础教程>>P172页
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
