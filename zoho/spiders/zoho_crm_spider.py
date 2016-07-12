import json
import scrapy
from zoho.items import Record


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
        'FEED_FORMAT': 'jsonlines',
        'FEED_URI': 's3://zoho-crm-api-dev/scraping/feeds/%(name)s/%(time)s.json',
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
            yield scrapy.Request(url, meta={'module': row['content']}, callback=self.parse_module_content)

    def has_data(self):
        try:
            self.json_data['response']['nodata']
        except KeyError:
            print('No valid data.')
            return True
        else:
            return False

    def is_json_valid(self):
        # Error in response
        try:
            self.json_data['response']['error']
        except KeyError:
            print('JSON is invalid.')
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

    def parse_module_content(self, response):
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
            print('JSON could not be deserialized')

        # Ensure dataset is not empty
        if not self.has_data():
            return

        # Verify JSON is valid
        if not self.is_json_valid():
            return

            # code: data['response']['error']['code']
            # code: 4100, Unable to populate data
            # code: 4600, Unable to process your request

        # TODO: Complete parsing of valid data
        for row in self.json_data['response']['result'][module]['row']:
            record = Record()
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