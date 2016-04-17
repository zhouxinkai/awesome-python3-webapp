import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

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
	args = []
	params = inspect.signature(fn).parameters
	for name, param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			args.append(name)
	return tuple(args)
	# 返回函数的形参元组

def get_all_kw_args(fn):
	# 如果url处理函数需要传入关键字参数，获取这个key
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)
 
def has_kw_arg(fn):
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
		self._all_kw_args = get_all_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)

	@asyncio.coroutine
	def __get_request_content(self, request):
		request_content = None

		if self._has_var_kw_arg or self._has_kw_arg or self._required_kw_args:
		# 确保URL处理函数有参数	
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content-Type')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = yield from request.json()
					if not isinstance(params, dict):
						return web.HTTPBadRequest('JSON body must be object.')
					request_content = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('application/form-data'):
					params = yield from request.post()
					request_content = dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)

			if request.method == 'GET':
				qs = request.query_string
				if qs:
					request_content = dict()
					for k, v in parse.parse_qs(qs, True).items():
						request_content[k] = v[0]
						# 解析url中?后面的键值对内容保存到request_content
						'''
						qs = 'first=f,s&second=s'
						parse.parse_qs(qs, True).items()	
						>>> dict([('first', ['f,s']), ('second', ['s'])])
						'''
						
		return request_content

	# __call__方法的代码逻辑:
	# 1.定义kw对象，用于保存参数
	# 2.判断URL处理函数是否存在参数，如果存在则根据是POST还是GET方法将request请求内容保存到kw
	# 3.如果kw为空(说明request没有请求内容)，则将match_info列表里面的资源映射表赋值给kw；如果不为空则把命名关键字参数的内容给kw
	# 4.完善_has_request_arg和_required_kw_args属性
	@asyncio.coroutine
	def __call__(self, request):
		request_content = yield from self.__get_request_content(request)
		logging.info(type(request_content))
		if request_content is None:
		# 参数为空说明没有从request对象中获取到参数,或者URL处理函数没有参数
			'''
			def hello(request):
				    text = '<h1>hello, %s!</h1>' % request.match_info['name']
				    return web.Response() 
			app.router.add_route('GET', '/hello/{name}', hello)
			'''
			if not self._has_var_kw_arg and not self._has_kw_arg and not self._required_kw_args:
				# 当URL处理函数没有参数时，将request.match_info设为空，防止调用出错
				request_content = dict()
			else:
				request_content = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._all_kw_args:
				# not的优先级比and的优先级要高
				# remove all unamed request_content， 从request_content中删除URL处理函数中所有不需要的参数
				for name in self.request_content:
					if not name in _all_kw_args:
						request_content.pop(name)
			# check named arg: 检查关键字参数的名字是否和match_info中的重复
			for k, v in request.match_info.items():
				if k in request_content:
					logging.warning('Duplicate arg name in named arg and kw args %s' % k)
				request_content[k] = v

		if self._has_request_arg:
		# 如果有request这个参数，则把request对象加入request_content['request']	
			request_content['request'] = request

		if self._required_kw_args:
		# check required request_content,检查是否有必需关键字参数	
			for name in self._required_kw_args:
				if not name in request_content:
					return web.HTTPBadRequest('Missing argument: %s' % name)

		# 以上代码均是为了获取调用参数
		logging.info('call with args: %s' % str(request_content))

		try:
			r = yield from self._func(**request_content)
			return r
		except APIError as e:
			return dict(error = e.error, data = e.data, message = e.message)

# 添加CSS等静态文件所在路径
def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
	# URL处理函数
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s.' % str(fn))
	if not asyncio.iscoroutine(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
		#用asyncio.coroutine装饰函数fn
	logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ','.join(inspect.signature(fn).parameters.keys())))
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
