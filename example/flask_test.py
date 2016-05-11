#!/usr/bin/env python
# -*- coding: utf-8 -*-
from flask import Flask
from flask import request

app = Flask(__name__)

@app.route('/', methods = ['GET', 'POST'])
def home():
	return '<h1>Home</h1>'

@app.route('/signin', methods = ['GET'])
def signin_from():
    return '''<form action="/signin" method="post">
              <p><input name="username"></p>
              <p><input name="password" type="password"></p>
              <p><button type="submit">Sign In</button></p>
              </form>'''

@app.route('/signin', methods = ['POST'])
def signin():
	if request.form['username'] == 'admin' and request.form['password'] == 'password':
		return '<h3>Hello, admin!</h3>'
	return '<h3>Bad username or password.</h3>'

if __name__ == '__main__':
	# 当一个py文件作为脚本运行时，变量__name__的值是'__main__',而作为模块导入时，__name__的值被设定为模块的名字
	app.run(debug = True)