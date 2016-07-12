from scrapy.settings import Settings
import json
import scrapy
from zoho.items import Module
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.utils.log import configure_logging
from zoho.items import ZohoItem

from scrapy.selector import Selector
from scrapy.http import HtmlResponse

MODULES = []


class ModuleSpider(scrapy.Spider):
    name = "zoho"
    allowed_domains = ["zoho.com"]
    start_urls = [
        "https://crm.zoho.com/crm/private/json/Info/getModules?authtoken={0}&scope=crmapi".format(
            '9354d7363a28608a9e3878c2084d8dfd')
    ]

    # Module spider runs
    # callback to `parse`
    # Record spider runs for each Module
    # Records output to S3

    custom_settings = {
        'ZOHO_CRM_AUTH_TOKEN': '9354d7363a28608a9e3878c2084d8dfd'
    }

    def parse(self, response):
        data = json.loads(response.body.decode())
        for row in data['response']['result']['row']:
            # Add to global modules list
            MODULES.append(row['content'])


class RecordSpider(scrapy.Spider):
    name = "zoho-record"
    allowed_domains = ["zoho.com"]

    custom_settings = {
        'FEED_FORMAT': 'jsonlines',
        'FEED_URI': 's3://zoho-crm-api-dev/scraping/feeds/%(name)s/%(time)s.json',
        'ZOHO_CRM_AUTH_TOKEN': '9354d7363a28608a9e3878c2084d8dfd'
    }
    json_data = None

    def __init__(self, *args, **kwargs):
        super(RecordSpider, self).__init__(*args, **kwargs)

        if not MODULES:
            raise ValueError('No modules given')

        # Generate dynamic URLs from acquired modules
        urls = []
        for module in MODULES:
            urls.append("https://crm.zoho.com/crm/private/json/{0}/getRecords?authtoken={1}&scope=crmapi".format(module,
                                                                                                                 '9354d7363a28608a9e3878c2084d8dfd'))
        self.start_urls = urls

    # Determine if json exists and is valid
    def is_json_valid(self):
        # Error in response
        try:
            self.json_data['response']['error']
        except KeyError:
            return True
        else:
            return False

    # Determine if passed `response` is valid
    @staticmethod
    def is_response_valid(response):
        try:
            response.status
        except AttributeError:
            return False

        if response.status == 200:
            return True
        else:
            return False

    def parse(self, response):
        if not self.is_response_valid(response):
            return

        # Attempt JSON deserialization
        try:
            self.json_data = json.loads(response.body.decode())
        except ValueError:
            print('JSON could not be deserialized')

        if not self.is_json_valid():
            return
        # code: data['response']['error']['code']
        # code: 4100, Unable to populate data
        # code: 4600, Unable to process your request
        # for row in self.json_data['response']['result']['row']:
        #     module = Module()
        #     module['id'] = row['id']
        #     module['name'] = row['content']
        #     module['number'] = row['no']
        #     yield module


configure_logging()
runner = CrawlerRunner()


@defer.inlineCallbacks
def crawl():
    yield runner.crawl(ModuleSpider)
    yield runner.crawl(RecordSpider)
    reactor.stop()


crawl()
reactor.run()  # the script will block here until the last crawl call is finished