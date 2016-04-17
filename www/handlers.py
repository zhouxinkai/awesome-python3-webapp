'url handlers, 处理各种URL请求'

import re, time, json, logging, hashlib, base64, asyncio

from web_framework import get, post

from models import User, Comment, Blog, next_id

from apis import Page, APIValueError, APIResourceNotFoundError, APIError

'''@get('/')
@asyncio.coroutine
# 制定url是'/'的处理函数为index
def index(request):
	users = yield from User.findAll()
	return{
		'__template__': 'test.html',
		'users': users
		#'__template__'指定的模板文件是test.html，其他参数是传递给模板的数据
	}'''

@get('/')
def index(request):
	summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
	blogs = [
		Blog(id = '1', name = 'Test Blog', summary = summary, created_at = time.time() - 120),
		Blog(id = '2', name = 'Something New', summary = summary, created_at = time.time() - 3600),
		Blog(id = '3', name = 'Learn Swift', summary = summary, created_at = time.time() - 7200)
	]
	return {
		'__template__': 'blogs.html',
		'blogs': blogs
	}

def get_page_index(page_str):
	p  = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p < 1:
		p = 1
	return p

@get('/api/users')
@asyncio.coroutine
def api_get_users(*, page = '1'):
	page_index = get_page_index(page)
	# 获取到要展示的博客页数是第几页
	user_count = yield from User.findNumber('count(id)')
	# count为MySQL中的聚集函数，用于计算某列的行数
	# user_count代表了有多个用户id
	p = Page(user_count, page_index, page_size = 2)
	# 通过Page类来计算当前页的相关信息, 其实是数据库limit语句中的offset，limit

	if user_count == 0:
		return dict(page = p, users = ())
	else:
		users = yield from User.findAll(orderBy = 'created_at desc', limit = (p.offset, p.limit))
		# page.offset表示从那一行开始检索，page.limit表示检索多少行
	for u in users:
		u.passwd = '******************'
	return dict(page = p, users = users)