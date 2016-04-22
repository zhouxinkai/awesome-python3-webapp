# PureBlog
一个用python3.5.1实现的个人博客网站，内含自己实现的简易版ORM框架和Web框架，欢迎查看学习。如果喜欢的话，可以点击右上角的Star按钮支持下我的工作^_^

演示网站PureBlog: [点我查看](http://115.28.155.42/)

演示使用管理员账号:

用户名：test@163.com

密码：test123



基本按照[廖雪峰的python教程](http://www.liaoxuefeng.com/)实战部分来编写，添加了大量注释。如果部分注释不够清楚和完整，也欢迎您来添加更多注释，欢迎发起pull request来完善注释和功能。

# 准备工作
请确保你已经安装以下的库

1. python3.5 及以上版本

2. aiohttp: 支持异步http服务器

3. jinja2: python的模板引擎

4. aiomysql: aiomysql针对asyncio框架用于访问mysql的库


所有的库都可以通过pip安装

# 代码结构
    www
		- static:存放静态资源
		- templates:存放模板文件
		- app.py: HTTP服务器以及处理HTTP请求；拦截器、jinja2模板、URL处理函数注册等
		- orm.py: ORM框架
		- web_frame.py(廖老师教程中的coroweb.py): 封装aiohttp，即写个装饰器更好的从Request对象获取参数和返回Response对象
		- apis.py: 定义几个错误异常类和Page类用于分页
		- config_default.py:默认的配置文件信息
		- config_override.py:自定义的配置文件信息
		- config.py:默认和自定义配置文件合并
		- markdown2.py:支持markdown显示的插件
		- pymonnitor.py: 用于支持自动检测代码改动重启服务
		- test_orm.py: 用于测试orm框架的正确性


## orm.py实现思路

1. 实现ModelMetaclass，主要完成类属性域和特殊变量直接的映射关系，方便Model类中使用。同时可以定义一些默认的SQL处理语句

2. 实现Model类,包含基本的get,set方法用于获取和设置变量域的值。同时实现相应的SQL处理函数（这时候可以利用ModelMetaclass自动根据类实例封装好的特殊变量)

3. 实现基本的数据库类型类，在应用层用户只要使用这种数据库类型类即可，避免直接使用数据的类型增加问题复杂度

## web框架实现思路

web框架在此处主要用于对aiohttp库的方法做更高层次的封装，用于抽离一些可复用的操作简化过程。主要涉及的封装内容为：

 - 定义装饰器@get()和@post()用与自动获取URL路径中的基本信息
 - 定义RequestHandler类，该类的实例对象获取完整的URL参数信息并且调用对应的URL处理函数（类中的方法）
 - 定义add_router方法用于注册对应的方法，即找到合适的fn给app.router.add_route()方法。该方法是aiohttp提供的接口，用于指定URL处理函数

 综上，处理一个请求的过程即为：

 1. app.py中注册所有处理函数、初始化jinja2、添加静态文件路径

 2. 创建服务器监听线程

 3. 收到一个request请求
 4. 经过几个拦截器(middlewares)的处理(app.py中的app = web.Application..这条语句指定)
 5. 调用RequestHandler实例中的__call__方法；再调用__call__方法中的post或者get方法
 5. 从已经注册过的URL处理函数中(handler.py)中获取对应的URL处理方法

注意：
1. asyncio不支持async/await关键字
2. mysql当中用特殊符号`(Tab键上面的符号)
3. 其他还有很多坑，可以参考我代码注释

## 关于部署的问题
1. 部署可以不采用廖老师所说的fabric，只需在linux服务器上安装git然后代码拷贝过来运行即可
2. Nginx配置文件中直接将反向代理交给你自己写的http服务器，也就是127.0.0.1:9000
3. 部署到服务器上之后记得修改页面__base__.html那几处ip为你的公网ip。

## 关于服务器的问题
服务器我采用CentOS 7，在使用过程需要先安装python3然后使用pip3安装相应的环境。CentOS上安装python3可以参考我的文章
[CentOS 7安装python3](http://kaimingwan.com/post/linux/centos-7an-zhuang-python3)


# 参考资料
1. [aiohttp官方文档](http://aiohttp.readthedocs.org/en/stable/web.html)
2. [廖雪峰的python教程](http://www.liaoxuefeng.com/)
3. [python3官方文档](https://docs.python.org/3/library/)
