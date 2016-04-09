#hello

import asyncio

@asyncio.coroutine
def wget(host):
	print('wget %s...' % host)
	connect = asyncio.open_connection(host, 80)
	response, request = yield from connect
	header = 'GET / HTTP/1.0\r\nHost: %s\r\n\r\n' % host
	request.write(header.encode('utf-8'))
	yield from request.drain()
	while True:
	    line = yield from response.readline()
	    if line == b'\r\n':
	        break
	    print('%s header > %s' % (host, line.decode('utf-8').rstrip()))
	# Ignore the body, close the socket
	request.close()

loop = asyncio.get_event_loop()
task = [wget(host) for host in ['www.sina.com', 'www.sohu.com', 'www.163.com']]
loop.run_until_complete(asyncio.wait(task))
loop.close()
