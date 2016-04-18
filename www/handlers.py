'url handlers, 处理各种URL请求'

import re, time, json, logging, hashlib, base64, asyncio

from web_framework import get, post

from models import User, Comment, Blog, next_id

from apis import Page, APIValueError, APIResourceNotFoundError, APIError

from config import configs

from aiohttp import web

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

'''
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
	return dict(page = p, users = users)'''

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

# 根据用户信息拼接一个cookie字符串
def user2cookie(user, max_age):
	# build cookie string by: id-expires-sha1
	expires = str(int(time.time()) + max_age)
	# 过期时间是当前时间+设置的有效时间
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	# 构建cookie存储的信息字符串
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	# SHA1是一种单向算法，即可以通过原始字符串计算出SHA1结果，但无法通过SHA1结果反推出原始字符串。
	return '-'.join(L)

# 根据cookie字符串，解析出用户相关信息
@asyncio.coroutine
def cookie2user(cookie_str):
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			# 如果不是3个元素的话，与我们当初构造sha1字符串时不符，返回None
			return None
		uid, expires, sha1 = L
		# 分别获取到用户id，过期时间和sha1字符串
		if int(expires) < time.time():
			# 如果超时(超过一天)，返回None
			return None
		user = yield from User.find(uid)
		# 根据用户id(id为primary key)查找库，对比有没有该用户
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
		# 根据查到的user的数据构造一个校验sha1字符串
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None

		user.passwd = '*******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

@get('/')
@asyncio.coroutine
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

# 注册页面
@get('/register')
@asyncio.coroutine
def register():
    return {
        '__template__': 'register.html'
    }

@post('/api/users')
@asyncio.coroutine
def api_register_user(*, email, name, passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
	# 判断email是否存在，且是否符合规定的正则表达式
		raise APIError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIError('passwd')

	users = yield from User.findAll('email=?', [email])
	# 查一下库里是否有相同的email地址，如果有的话提示用户email已经被注册过
	if len(users):
		raise APIError('register:failed', 'email', 'Email is already in use.')

	uid = next_id()
	# 生成一个当前要注册用户的唯一uid
	sha1_passwd = '%s:%s' % (uid, passwd)

	admin = False
	if email == 'admin@163.com':
		admin = True

	# 创建一个用户（密码是通过sha1加密保存）
	user = User(id = uid, name = name.strip(), email = email, passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
		image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest(), admin=admin)
	# 注意数据库中存储的passwd是经过SHA1计算后的40位Hash字符串，所以服务器端并不知道用户的原始口令。

	yield from user.save()
	# 保存这个用户到数据库用户表
	logging.info('save user OK')
	r = web.Response()
	# 构建返回信息
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
	# 86400代表24小时
	user.passwd = '******'
	# 只把要返回的实例的密码改成'******'，库里的密码依然是正确的，以保证真实的密码不会因返回而暴漏
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii = False, default = lambda o:o.__dict__).encode('utf-8')
	return r

# 登陆页面
@get('/signin')
@asyncio.coroutine
def signin():
    return {
        '__template__': 'signin.html'
    }


@post('/api/authenticate')
@asyncio.coroutine
def authenticate(*, email, passwd):
	if not email:
		raise APIValueError('email', 'Invalid email.')
	if not passwd:
		raise APIValueError('passwd', 'Invalid password.')

	users = yield from User.findAll('email=?', [email])
	# 根据email在库里查找匹配的用户
	if not len(users):
		raise APIValueError('email', 'email not exist')
	user = users[0]

	browser_sha1_passwd = '%s:%s' % (user.id, passwd)
	browser_sha1 = hashlib.sha1(browser_sha1_passwd.encode('utf-8'))
	'''sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	# 在Python 3.x版本中，把'xxx'和u'xxx'统一成Unicode编码，即写不写前缀u都是一样的，而以字节形式表示的字符串则必须加上b前缀：b'xxx'。
	sha1.update(passwd.encode('utf-8'))'''
	if user.passwd != browser_sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid passwd')
	
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
	user.passwd = '*********'
	# 只把要返回的实例的密码改成'******'，库里的密码依然是正确的，以保证真实的密码不会因返回而暴漏
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii = False, default = lambda o:o.__dict__).encode('utf-8')
	return r    