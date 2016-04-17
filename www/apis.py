import json
import logging
import inspect
import functools

# 简单的几个api错误异常类，用于跑出异常


class APIError(Exception):

    def __init__(self, error, data='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.data = data
        self.message = message


class APIValueError(APIError):

    """docstring for APIValueError"""

    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)


class APIResourceNotFoundError(APIError):

    """docstring for APIResourceNotFoundError"""

    def __init__(self, arg):
        super(APIResourceNotFoundError, self).__init__(
            'value:notfound', field, message)


class APIPermissionError(object):

    """docstring for APIPermissionError"""

    def __init__(self, arg):
        super(APIPermissionError, self).__init__(
            'permission:forbidden', 'permission', message)


# 用于分页
class Page(object):

    """docstring for Page"""
    # 参数说明：
    # item_count：要显示的条目数量
    # page_index：要显示的是第几页
    # page_size：每页的条目数量，为了方便测试现在显示为2条

    def __init__(self, item_count, page_index=1, page_size=2):
        self.__item_count = item_count
        self.__page_size = page_size
        # 计算出应该有多少页才能显示全部的条目
        self.__page_count = item_count // page_size + \
            (1 if item_count % page_size > 0 else 0)
        # 如果没有条目或者要显示的页超出了能显示的页的范围
        if (item_count == 0) or (page_index > self.__page_count):
            # 则不显示
            self.offset = 0
            self.limit = 0
            self.__page_index = 1
        else:
            # 否则说明要显示
            # 设置显示页就是传入的要求显示的页
            self.__page_index = page_index
            # 这页的初始条目的offset
            self.offset = self.__page_size * (page_index - 1)
            # 这页能显示的数量
            self.limit = self.__page_size
        # 这页后面是否还有下一页
        self.has_next = self.__page_index < self.__page_count
        # 这页之前是否还有上一页
        self.has_previous = self.__page_index > 1

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.__item_count, self.__page_count, self.__page_index, self.__page_size, self.offset, self.limit)

    __repr__ = __str__
