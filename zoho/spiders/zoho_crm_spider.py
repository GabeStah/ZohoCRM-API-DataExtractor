import json
import scrapy
import logging
from zoho.items import Record


class ModuleSpider(scrapy.Spider):
    allowed_domains = ["zoho.com"]
    auth_token = '9354d7363a28608a9e3878c2084d8dfd'
    base_get_records_url = "https://crm.zoho.com/crm/private/json/{0}/getRecords?authtoken={1}&scope=crmapi&fromIndex=1&toIndex=200"
    debug = True
    json_data = None
    name = "zoho"
    response = None
    start_urls = [
        "https://crm.zoho.com/crm/private/json/Info/getModules?authtoken={0}&scope=crmapi&type=api".format(auth_token)
    ]

    # Module spider runs
    # callback to `parse`
    # Record spider runs for each Module
    # Records output to S3

    custom_settings = {
        'FEED_FORMAT': 'jsonlines',
        'FEED_URI': 's3://zoho-crm-api-dev/scraping/feeds/%(name)s/%(time)s.json',
        'ZOHO_CRM_AUTH_TOKEN': '9354d7363a28608a9e3878c2084d8dfd'
    }

    def __init__(self, *args, **kwargs):
        super(ModuleSpider, self).__init__(*args, **kwargs)

    # Determine if API indicated data is missing (empty DB table or query)
    def has_data(self):
        try:
            self.json_data['response']['nodata']
        except KeyError:
            return True
        else:
            logging.debug('No data was found matching query, url: {0}.'.format(self.response.url))
            return False

    # Determine if API indicated error in retrieved JSON
    def is_json_valid(self):
        # Error in response
        try:
            self.json_data['response']['error']
        except KeyError:
            return True
        else:
            logging.debug('JSON is invalid, url: {0}.'.format(self.response.url))
            return False

    # Determine if passed `response` is valid
    @staticmethod
    def is_response_valid(response):
        try:
            response.status
        except AttributeError:
            logging.debug('Invalid response, url: {0}.'.format(response.url))
            return False

        if response.status == 200:
            return True
        else:
            logging.debug('Invalid response, url: {0}.'.format(response.url))
            return False

    # Initial parse to retrieve `Module` data
    def parse(self, response):
        self.response = response
        data = json.loads(response.body.decode())

        for row in data['response']['result']['row']:
            module = row['content']
            url = self.base_get_records_url.format(module, self.auth_token)
            # Parse record content for each module
            yield scrapy.Request(url, meta={'module': module}, callback=self.parse_module_content)

    # Secondary parse for each `Module` to retrieve `Records` and output to feed
    def parse_module_content(self, response):
        # code: data['response']['error']['code']
        # code: 4100, Unable to populate data
        # code: 4600, Unable to process your request
        self.response = response
        # Passed module
        module = response.meta['module']
        if not module:
            return

        # Validate response
        if not self.is_response_valid(response):
            return

        # Attempt JSON deserialization
        try:
            self.json_data = json.loads(response.body.decode())
        except ValueError:
            logging.debug('JSON could not be deserialized, url: {0}.'.format(self.response.url))
            return

        # Ensure dataset is not empty
        if not self.has_data():
            return

        # Verify JSON is valid
        if not self.is_json_valid():
            return

        # TODO: Complete parsing of valid data
        #records = list()
        logging.info('Data retrieved for module: {0}, url: {1}'.format(module, self.response.url))
        for row in self.json_data['response']['result'][module]['row']:
            record = Record()
            if self.debug:
                record['module'] = module
            for FL in row['FL']:
                record[FL['val']] = FL['content']
            yield record

        # ALTERNATIVE METHOD
        # items = []
        # for site in sites:
        #     item = Website()
        #     item['name'] = site.xpath('a/text()').extract()
        #     item['url'] = site.xpath('a/@href').extract()
        #     item['description'] = site.xpath('text()').re('-\s[^\n]*\\r')
        #     items.append(item)
        # return items