# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.item import Field


class Record(scrapy.Item):
    """The basic `scrapy.Item` subclass to house all `Item` generation.  The `__setitem__` method override ensures
     that pre-defined key values don't need to be assigned.

    :param scrapy.Item: Inherited `scrapy.Item`
    :type scrapy.Item: scrapy.Item
    """
    def __setitem__(self, key, value):
        """Meta method which attaches the passed `key` and `value` pair to this `Record` class instance.

        :param key: Key value.
        :type key: str
        :param value: Value to assign to `key`.
        :type value: object
        :return: Nothing
        :rtype: None
        """
        if key not in self.fields:
            self.fields[key] = Field()
        self._values[key] = value
