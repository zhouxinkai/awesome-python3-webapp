#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import logging
import inspect
import functools

_PAGE_SIZE = 20

# 简单的几个api错误异常类，用于跑出异常


'''
JSON API definition.
'''

class APIError(Exception):
    '''
    the base APIError which contains error(required), field(optional) and message(optional).
    '''
    def __init__(self, error, field='', message=''):
        super(APIError, self).__init__(message)
        self.error = error
        self.field = field
        self.message = message

class APIValueError(APIError):
    '''
    Indicate the input value has error or invalid. The field specifies the error field of input form.
    '''
    def __init__(self, field, message=''):
        super(APIValueError, self).__init__('value:invalid', field, message)

class APIResourceNotFoundError(APIError):
    '''
    Indicate the resource was not found. The field specifies the resource name.
    '''
    def __init__(self, field, message=''):
        super(APIResourceNotFoundError, self).__init__('value:notfound', field, message)

class APIPermissionError(APIError):
    '''
    Indicate the api has no permission.
    '''
    def __init__(self, message=''):
        super(APIPermissionError, self).__init__('permission:forbidden', 'permission', message)


# 用于分页
class Page(object):

    """docstring for Page"""
    # 参数说明：
    # item_count：要显示的条目数量
    # page_index：要显示的是第几页
    # page_size：每页的条目数量，为了方便测试现在显示为10条

    def __init__(self, item_count, page_index=1, page_size=_PAGE_SIZE):
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
