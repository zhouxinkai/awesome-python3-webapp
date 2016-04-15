import logging; logging.basicConfig(level=logging.INFO)

import asyncio, os, json, time
from datetime import datetime

from aiohttp import web

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

@asyncio.coroutine
def logger_factory(app, handler):
	@asyncio.coroutine
	def logger(request):
		# 记录日志:
		logging.info('Request: %s %s' % (request.method, request.path))
		#继续处理请求:
		return （yield from handler(request)）
	return logger

app = web.Application(loop = loop, middlewares = [logger_factory, response_factory])
init_jinja2(app, filters = dict(datetime = datetime_filter))
add_routes(app, 'handlers')
app_static(app)