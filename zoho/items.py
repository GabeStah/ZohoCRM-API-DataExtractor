# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Module(scrapy.Item):
    id = scrapy.Field()
    number = scrapy.Field()
    name = scrapy.Field()


class Record(scrapy.Item):
    id = scrapy.Field()
    number = scrapy.Field()
    name = scrapy.Field()


class ZohoItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    title = scrapy.Field()
    link = scrapy.Field()
    desc = scrapy.Field()
