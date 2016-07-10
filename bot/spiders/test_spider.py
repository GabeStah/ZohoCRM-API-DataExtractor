import scrapy


class BotSpider(scrapy.Spider):
    name = "bot"
    allowed_domains = ["google.com"]
    start_urls = [
        "http://www.google.com"
    ]

    def parse(self, response):
        filename = response.url.split("/")[-2] + '.html'
        with open(filename, 'wb') as f:
            f.write(response.body)