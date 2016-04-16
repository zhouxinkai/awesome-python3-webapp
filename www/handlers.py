'url handlers, 处理各种URL请求'

import re, time, json, logging, hashlib, base64, asyncio

from web_framework import get, post

from models import User, Comment, Blog, next_id

@get('/')
@asyncio.coroutine
# 制定url是'/'的处理函数为index
def index(request):
	users = yield from User.findAll()
	return{
		'__template__': 'test.html',
		'users': users
		#'__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
	}