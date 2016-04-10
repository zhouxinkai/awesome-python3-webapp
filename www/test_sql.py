import orm,asyncio
from models import User,Blog,Comment

@asyncio.coroutine
def test(loop):
    yield from orm.create_pool(loop=loop, user='root', password='683004', database='awesome')
    u=User(name='test3',email='test4@test.com',passwd='test',image='about:blank')
    yield from u.save()

loop = asyncio.get_event_loop()
loop.run_until_complete(test(loop))
loop.close()