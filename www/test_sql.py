import orm,asyncio
from models import User,Blog,Comment

@asyncio.coroutine
def test(loop):
    yield from orm.create_pool(loop=loop, user='root', password='683004', database='awesome', port = 3307)
    u=User(name='bruce_zhou', email='846673264@qq.com', passwd='usrmnm2052.0', image='about:blank')
    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()
