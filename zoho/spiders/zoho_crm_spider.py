import datetime
import json
import scrapy
import logging

from zoho.items import Record


class ModuleSpider(scrapy.Spider):
    AUTH_TOKEN = '9354d7363a28608a9e3878c2084d8dfd'
    BASE_GET_RECORDS_URL = "https://crm.zoho.com/crm/private/json/{module}/getRecords?authtoken={auth_token}&scope=crmapi&fromIndex={from_index}&toIndex={to_index}"
    INITIAL_FROM_INDEX = 1
    MAX_RECORD_COUNT = 200

    allowed_domains = ["zoho.com"]
    json_data = None
    name = "zoho"
    response = None
    start_urls = [
        "https://crm.zoho.com/crm/private/json/Info/getModules?authtoken={auth_token}&scope=crmapi&type=api".format(auth_token=AUTH_TOKEN)
    ]

    # Module spider runs
    # callback to `parse`
    # Record spider runs for each Module
    # Records output to S3

    def __init__(self, *args, **kwargs):
        super(ModuleSpider, self).__init__(*args, **kwargs)
        # Set starting timestamp
        self.timestamp = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
        self.timestamp_concatenated = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())

    # getRecords formatted URL with pagination
    def get_records_url(self, module, from_index):
        return self.BASE_GET_RECORDS_URL.format(
            auth_token=self.AUTH_TOKEN,
            module=module,
            from_index=from_index,
            to_index=self.to_index(from_index)
        )

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

    # Determine if passed `module_name` is in settings whitelist (if altered)
    def is_module_allowed(self, module_name):
        modules = self.settings.get('ZOHO_MODULE_WHITELIST')
        if type(modules) is str:
            if (modules.upper() == 'ALL') or modules == module_name:
                return True
        elif type(modules) is list:
            for module in modules:
                if module.upper() == 'ALL' or module == module_name:
                    return True
        return False

    # Initial parse to retrieve `Module` data
    def parse(self, response):
        self.response = response
        data = json.loads(response.body.decode())

        for row in data['response']['result']['row']:
            module = row['content']
            # Ensure module is on approved whitelist
            if self.is_module_allowed(module):
                url = self.get_records_url(module, self.INITIAL_FROM_INDEX)
                # Parse record content for each module
                yield scrapy.Request(url,
                                     meta={'module': module,
                                           'from_index': self.INITIAL_FROM_INDEX},
                                     callback=self.parse_module_content)

    # Secondary parse for each `Module` to retrieve `Records` and output to feed
    def parse_module_content(self, response):
        # TODO: Detect most recent execution date/time from either S3 timestamped directory or provided user setting
        # code: data['response']['error']['code']
        # code: 4100, Unable to populate data
        # code: 4600, Unable to process your request
        self.response = response
        # Passed module
        module = response.meta['module']

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

        logging.info('Data retrieved for module: {0}, url: {1}'.format(module, self.response.url))
        for row in self.json_data['response']['result'][module]['row']:
            record = Record()
            if self.settings.get('ZOHO_INCLUDE_MODULE_NAME'):
                record['module'] = module
            for FL in row['FL']:
                record[FL['val']] = FL['content']
            yield record

        # Generate next paginated URL
        from_index = response.meta['from_index']
        next_from_index = self.MAX_RECORD_COUNT + from_index
        next_url = self.get_records_url(module, next_from_index)
        # Skip if output record maximum is exceeded
        if self.settings.get('OUTPUT_MAXIMUM_RECORDS') and next_from_index > self.settings.get('OUTPUT_MAXIMUM_RECORDS'):
            return
        # Parse record content for each module
        yield scrapy.Request(next_url,
                             meta={'module': module,
                                   'from_index': next_from_index},
                             callback=self.parse_module_content)

    # Calculate the `to_index` for pagination
    def to_index(self, from_index):
        return from_index + self.MAX_RECORD_COUNT - 1
