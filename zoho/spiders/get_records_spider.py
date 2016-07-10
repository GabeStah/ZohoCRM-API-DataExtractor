import json
import scrapy
from zoho.items import Record


class ZohoCRMSpider(scrapy.Spider):
    name = "zoho"
    allowed_domains = ["zoho.com"]
    start_urls = [
        "https://crm.zoho.com/crm/private/json/Leads/getRecords?authtoken={0}&scope=crmapi".format('9354d7363a28608a9e3878c2084d8dfd')
    ]

    custom_settings = {
        'FEED_FORMAT': 'json',
        'FEED_URI': 's3://zoho-crm-api-dev/scraping/feeds/%(name)s/%(time)s.json',
        'ZOHO_CRM_AUTH_TOKEN': '9354d7363a28608a9e3878c2084d8dfd'
    }

    def parse(self, response):
        data = json.loads(response.body.decode())
        for row in data['response']['result']['row']:
            module = Record()
            module['id'] = row['id']
            module['name'] = row['content']
            module['number'] = row['no']
            yield module
