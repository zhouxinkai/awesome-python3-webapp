import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from config import configs
import orm

from web_framework import add_routes, add_static

from handlers import cookie2user, COOKIE_NAME

#from handlers import cookie2user, COOKIE_NAME

'''
# 这是一个使用aiohttp的简单例子
def index(request):
    return web.Response(body=b'<h1>Awesome</h1>')

@asyncio.coroutine
def init(loop):
    app = web.Application(loop=loop)
    app.router.add_route('GET', '/', index)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()'''

def init_jinja2(app, **kw):
	logging.info('init jinja2....')
	options = dict(
		autoescape = kw.get('autoescape', True),
		block_start_string = kw.get('block_start_string', '{%'),	# 运行代码的开始标识符
		block_end_string = kw.get('block_end_string', '%}'),	# 运行代码的结束标识符
		variable_start_string = kw.get('variable_start_string', '{{'),	# 变量的开始标识符
		variable_end_string = kw.get('variable_end_string', '}}'),	# 变量的结束标识符
		auto_reload  =kw.get('auto_reload', True)
	)

	path = kw.get('path', None)
	#从参数中获取path字段，即模板文件的位置
	if path is None:
		# 如果没有，则默认为当前文件目录下的 templates 目录
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s' % path)

	env = Environment(loader = FileSystemLoader(path), **options)
	# Environment是jinjia2中的一个核心类，它的实例用来保存配置、全局对象以及模板文件的路径
	filters = kw.get('filters', None)
	# filters: 一个字典描述的filters过滤器集合, 如果非模板被加载的时候, 可以安全的添加或较早的移除.
	if filters is not None:
		for name, f in filters.items():
			env.filters[name] = f

	app['__templating__'] = env
	# 给webapp设置模板

async def logger_factory(app, handler):
	async def logger(request):
		# 记录日志:
		logging.info('Request: %s %s' % (request.method, request.path))
		#继续处理请求:
		return (await handler(request))
	return logger

@asyncio.coroutine
def auth_factory(app, handler):
	@asyncio.coroutine
	def auth(request):
		logging.info('check user: %s %s' % (request.method, request.path))
		request.__user__ = None

		cookie_str = request.cookies.get(COOKIE_NAME)
		# 获取到cookie字符串, cookie是用分号分割的一组名值对，在python中被看成dict
		if cookie_str:
			user = yield from cookie2user(cookie_str)
			# 通过反向解析字符串和与数据库对比获取出user
			if user:
				logging.info('set current user: %s' % user.email)
				request.__user__ = user
				# user存在则绑定到request上
		'''if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
			return web.HTTPFound('/signin')'''
		
		# 继续执行下一步
		return (yield from handler(request))
	return auth

# ***********************************************响应处理（重点，重点，重点，重要的事说三遍）***************************************************
# 总结一下
# 请求对象request的处理工序流水线先后依次是：
#     	logger_factory->response_factory->RequestHandler().__call__->get或post->handler
# 对应的响应对象response的处理工序流水线先后依次是:
#     	由handler构造出要返回的具体对象
#     	然后在这个返回的对象上加上'__method__'和'__route__'属性，以标识别这个对象并使接下来的程序容易处理
#     	RequestHandler目的就是从请求对象request的请求content中获取必要的参数，调用URL处理函数,然后把结果返回给response_factory
#     	response_factory在拿到经过处理后的对象，经过一系列类型判断，构造出正确web.Response对象，以正确的方式返回给客户端
# 在这个过程中，我们只用关心我们的handler的处理就好了，其他的都走统一的通道，如果需要差异化处理，就在通道中选择适合的地方添加处理代码。
# 注： 在response_factory中应用了jinja2来渲染模板文件

async def response_factory(app, handler):
	async def response(request):
		logging.info('Response handler...')
		r = (await handler(request))
		# 调用相应的URL处理函数处理请求
		logging.info('response result = %s' % str(r))

		if isinstance(r, web.StreamResponse):
			return r
		if isinstance(r, bytes):
		# 如果响应结果为字节流，则把字节流塞到response的body里，设置响应类型为流类型，返回	
			resp = web.Response(body = r)
			resp.content_type = 'application/octet-stream'
			return resp
		if isinstance(r, str):
			if r.startswith('redirect:'):
				# 先判断是不是需要重定向，是的话直接用重定向的地址重定向
				return web.HTTPFound(r[9:])
			resp = web.Response(body = r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp

		if isinstance(r, dict):
			# 先查看一下有没有'__template__'为key的值
			template = r.get('__template__')
			if template is None:
				# 如果没有，说明要返回json字符串，则把字典转换为json返回，对应的response类型设为json类型
				resp = web.Response(body = json.dumps(
					r, ensure_ascii = False, default = lambda o:o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json'
				return resp
			else:
				r['__user__'] = request.__user__
				# 如果有'__template__'为key的值，则说明要套用jinja2的模板，'__template__'Key对应的为模板文件名
				# 得到模板文件然后用**r去渲染render
				resp = web.Response(body = app['__templating__'].get_template(
					template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp

			if isinstance(r, int) and r >=100 and r < 600:
				return web.Response(r)

			if isinstance(r, tuple) and len(r) == 2:
				status_code, description = r
				# 如果tuple的第一个元素是int类型且在100到600之间，这里应该是认定为status_code为http状态码，description为描述
				if isinstance(status_code. int) and t >= 100 and t < 600:
					return web.Response(status = status_code, text = str(description))
					resp.content_type = 'text/plain;charset=utf-8'
					return resp
		
	return response

def datetime_filter(t):
	second_gap = int(time.time() - t)
	# time.time()取得当前时间（新纪元开始后的秒数）
	if second_gap < 60:
		return u'1分钟前'
	if second_gap < 3600:
		return u'%s分钟前' % (second_gap//60)
		# 双斜线表示整除
	if second_gap < 86400:
		return u'%s小时前' % (second_gap//3600)
	if second_gap < 604800:
		return u'%s天前' % (second_gap//86400)
	dt = datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

async def init(loop):
	await orm.create_pool(loop = loop, **configs.db)
	# middlewares(中间件)设置3个中间处理函数(都是装饰器)
    # middlewares中的每个factory接受两个参数，app 和 handler(即middlewares中的下一个handler)
    # 譬如这里logger_factory的handler参数其实就是auth_factory
    # middlewares的最后一个元素的handler会通过routes查找到相应的，其实就是routes注册的对应handler
    # 这其实是装饰模式的典型体现，logger_factory, auth_factory, response_factory都是URL处理函数前（如handler.index）的装饰功能
	app = web.Application(loop=loop, middlewares=[
		logger_factory, auth_factory, response_factory
	])
	init_jinja2(app, filters = dict(datetime = datetime_filter))
	# 添加URL处理函数, 参数handlers为模块名
	add_routes(app, 'handlers')
	# 添加CSS等静态文件路径
	add_static(app)
	# 启动
	srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
	logging.info('server started at http://127.0.0.1:9000 ........')
	return srv

# 入口，固定写法
# 获取eventloop然后加入运行事件
loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()