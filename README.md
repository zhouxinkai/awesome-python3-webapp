# 从零开始用Python开发一个博客网站
我是跟着廖雪峰的Python教程一步一步走下来的，相信大家还记得在廖老师的<a href="http://www.liaoxuefeng.com/wiki/0014316089557264a6b348958f449949df42a6d3a2e542c000" target="_blank">Python3教程</a>刚开始的那段话

如果你是小白用户，满足以下条件：

 - 会使用电脑，但从来没写过程序；
 - 还记得初中数学学的方程式和一点点代数知识；
 - 想从编程小白变成专业的软件架构师；
 - 每天能抽出半个小时学习。
 
![image](http://www.liaoxuefeng.com/files/attachments/00138676512923004999ceca5614eb2afc5c0efdd2e4640000/0)

不要再犹豫了，这个教程就是为你准备的！
<hr>
不得不说廖老师的教程写的很用心，也为大家能坚持到最后点个赞，但后面的实战部分远没有那么容易，还是有一定难度的，比如**装饰器、元类**等等，由于就有了我这个，全部代码都是我<big><mark>**一行一行**</mark></big>思考过然后敲下来的，<big><mark>**内含大量注释**</mark></big>，保证你看完以后，python水平有一个<big><mark>**大大的提高**</mark></big>。

如果感觉还好的话，可以点击右上角的Star按钮支持下我的工作^_^

# 演示

演示网址: [点我点我](http://52.197.62.209:9000/)

管理员账号:

用户名：bruce_zhou@163.com

密码：bruce_zhou

注：我修改过代码可以不用管理员登录，就可以进行一系列操作


# 准备工作
请确保你已经安装以下的库

1. python3.5 及以上版本

2. aiohttp: 异步http服务器

3. jinja2: python的模板渲染引擎

4. aiomysql: 异步mysql库,[参考资料](http://aiomysql.readthedocs.io/en/latest/)

# 代码结构
>- www
	- static:存放静态资源
	- templates:存放模板文件
	- **app.py**: HTTP服务器以及处理HTTP请求；拦截器、jinja2模板、URL处理函数注册等
	- **orm.py**: ORM框架
	- **web_framework.py**(廖老师教程中的coroweb.py): 封装aiohttp，即写个装饰器更好的从Request对象获取参数和返回Response对象
	- apis.py: 定义几个错误异常类和Page类用于分页
	- config_default.py:默认的配置文件信息
	- config_override.py:自定义的配置文件信息
	- config.py:默认和自定义配置文件合并
	- markdown2.py:支持markdown显示的插件
	- pymonnitor.py: 用于支持自动检测代码改动重启服务

#### 其中重要的模块有三个：**orm.py、web_framework.py、app.py**，下面将分别介绍。

## orm.py实现思路
> ORM全称为对象关系映射(Object Relation Mapping)，即用一个类来对应数据库中的一个表，一个对象来对应数据库中的一行，表现在代码中，即用**类属性**来对应一个表，用**实例属性**来对应数据库中的一行。具体步骤如下：

1. 实现<strong>元类</strong>ModelMetaclass：创建一些特殊的类属性，用来完成类属性和表的映射关系，并定义一些默认的SQL语句

2. 实现Model类：包含基本的get,set方法用于获取和设置实例属性的值，并实现相应的SQL处理函数

3. 实现三个映射数据库表的类：User、Blog、Comment，在应用层用户只要使用这三个类即可

## web框架实现思路
> web框架在此处主要用于对aiohttp库做更高层次的封装，从简单的WSGI接口到一个复杂的web framework，本质上还是对request请求对象和response响应对象的处理，可以将这个过程想象成工厂中的一条流水线生产产品，request对象就是流水线的原料，这个原料在经过一系列的加工后，生成一个response对象返回给浏览器。


#### 具体到代码中去看，这条流水线的过程如下

 1. app.py中注册所有处理函数、初始化jinja2、添加静态文件路径
 
 2. 创建服务器监听线程
 
 3. 监听线程收到一个request请求
 
 4. 经过几个<strong>拦截器</strong>(middlewares)的处理(app.py中的app = web.Application..这条语句指定)
 
 5. 调用RequestHandler实例中的__call__方法；再调用__call__方法中的post或者get方法

 5. 调用响应的URL处理函数，并返回结果
 6. response_factory在拿到经URL处理函数返回过来的对象，经过一系列类型判断后，构造出正确web.Response对象，返回给客户端


# 我认真看过的一些文档
4. [深刻理解Python中的元类(metaclass) ------  深度5星级好文](http://blog.jobbole.com/21351/)
5. [理解python中的装饰器 ------  翻译自StackOverflow](http://www.wklken.me/posts/2013/07/19/python-translate-decorator.html)
6. [Python 面向对象（进阶篇）------  比较全和基础](http://www.imooc.com/article/3066)
7. [HTTP Get，Post请求详解 ------  5星级好文，排版可能有点乱，但写的真的很好](http://blog.chinaunix.net/uid-25808509-id-3047968.html)
8. [python3官方文档 ------  五星级推荐，很全](https://docs.python.org/3/library/)
9. [Google Python编码规范 —--- 良好的编程习惯是很重要的 ](http://zh-google-styleguide.readthedocs.org/en/latest/google-python-styleguide/python_style_rules/)
10. [  Python进阶必读汇总 -------认真看完，秒杀一大片](http://www.kuqin.com/shuoit/20151116/348975.html)
11. [Python 深入理解yield](http://www.jb51.net/article/15717.htm)
12. [Python SMTP发送邮件](http://www.runoob.com/python/python-email.html)
