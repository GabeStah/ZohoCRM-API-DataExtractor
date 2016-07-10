import scrapy
from bot.items import BotItem


class BotSpider(scrapy.Spider):
    name = "bot"
    allowed_domains = ["dmoz.org"]
    start_urls = [
        "http://www.dmoz.org/Computers/Programming/Languages/Python/Books/",
        "http://www.dmoz.org/Computers/Programming/Languages/Python/Resources/",
    ]

    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_URI': 's3://zoho-crm-api-dev/scraping/feeds/%(name)s/%(time)s.json'
    }

    def parse(self, response):
        for sel in response.xpath('//ul/li'):
            item = BotItem()
            item['title'] = sel.xpath('a/text()').extract()
            item['link'] = sel.xpath('a/@href').extract()
            item['desc'] = sel.xpath('text()').extract()
            yield item
