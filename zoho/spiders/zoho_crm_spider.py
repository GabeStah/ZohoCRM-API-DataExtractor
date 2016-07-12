from scrapy.settings import Settings
import json
import scrapy
from zoho.items import Module
from twisted.internet import reactor, defer
from scrapy.crawler import CrawlerRunner
from scrapy.crawler import CrawlerProcess
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

    auth_token = '9354d7363a28608a9e3878c2084d8dfd'
    base_url = "https://crm.zoho.com/crm/private/json/{0}/getRecords?authtoken={1}&scope=crmapi"
    json_data = None

    def __init__(self, *args, **kwargs):
        super(ModuleSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        data = json.loads(response.body.decode())
        # for row in data['response']['result']['row']:
        #     # Add to global modules list
        #     MODULES.append(row['content'])

        for row in data['response']['result']['row']:
            url = self.base_url.format(row['content'], self.auth_token)
            # Parse record content for each module
            yield scrapy.Request(url, callback=self.parse_module_content)

    def has_data(self):
        try:
            self.json_data['response']['nodata']
        except KeyError:
            print('No valid data.')
        else:
            return False

    def is_json_valid(self):
        # Error in response
        try:
            self.json_data['response']['error']
        except KeyError:
            print('JSON is invalid.')
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

    def parse_module_content(self, response):
        # Validate response
        if not self.is_response_valid(response):
            return

        # Attempt JSON deserialization
        try:
            self.json_data = json.loads(response.body.decode())
        except ValueError:
            print('JSON could not be deserialized')

        # Verify JSON is valid
        if not self.is_json_valid():
            return

        # Ensure dataset is not empty
        if not self.has_data():
            return
            # code: data['response']['error']['code']
            # code: 4100, Unable to populate data
            # code: 4600, Unable to process your request

        for row in self.json_data['response']['result']['row']:
            module = Module()
            module['id'] = row['id']
            module['name'] = row['content']
            module['number'] = row['no']
            yield module


class RecordSpider(scrapy.Spider):
    name = "zoho-record"
    allowed_domains = ["zoho.com"]

    custom_settings = {
        'AWS_ACCESS_KEY_ID': 'AKIAI7RHF4PAJONISB7A',
        'AWS_SECRET_ACCESS_KEY': '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',
        'FEED_FORMAT': 'json',
        'FEED_URI': 's3://zoho-crm-api-dev/scraping/feeds/%(name)s/%(time)s.json',
        'ZOHO_CRM_AUTH_TOKEN': '9354d7363a28608a9e3878c2084d8dfd'
    }
    json_data = None
    auth_token = '9354d7363a28608a9e3878c2084d8dfd'
    base_url = "https://crm.zoho.com/crm/private/json/{0}/getRecords?authtoken={1}&scope=crmapi"
    full_url = "https://crm.zoho.com/crm/private/json/Leads/getRecords?authtoken=9354d7363a28608a9e3878c2084d8dfd&scope=crmapi"

    def __init__(self, module='', *args, **kwargs):
        super(RecordSpider, self).__init__(*args, **kwargs)

        if not MODULES:
            raise ValueError('No modules given')

        self.module = module
        #if module:
            #raise ValueError('No module given')

            # Generate dynamic URLs from acquired modules

            # for module in MODULES:
            #     urls.append("https://crm.zoho.com/crm/private/json/{0}/getRecords?authtoken={1}&scope=crmapi".format(module, '9354d7363a28608a9e3878c2084d8dfd'))
            #urls.append(self.base_url.format(module, self.auth_token))

        urls = list()
        urls.append(self.full_url)
        #urls.append(self.base_url.format(self.module, self.auth_token))

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


process = CrawlerProcess({
    'USER_AGENT': 'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1)'
})

process.crawl(ModuleSpider)
process.start() # the script will block here until the crawling is finished

#for mod in MODULES:
#    process.crawl(RecordSpider(module=mod))
#process.start() # the script will block here until the crawling is finished

# @defer.inlineCallbacks
# def crawl():
#     yield runner.crawl(ModuleSpider)
#     for mod in MODULES:
#         yield runner.crawl(RecordSpider(module=mod))
#     reactor.stop()
#
# #if __name__ == "__main__":
# if __name__ == 'zoho.spiders.zoho_crm_spider':
#     configure_logging()
#     runner = CrawlerRunner()
#
#     crawl()
#     reactor.run()  # the script will block here until the last crawl call is finished
