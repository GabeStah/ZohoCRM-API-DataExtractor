import datetime
import json
import logging
import scrapy
from urllib.parse import urlencode

from zoho.items import Record


class ModuleSpider(scrapy.Spider):
    ZOHO_BASE_MODULES_URL = "https://crm.zoho.com/crm/private/json/Info/getModules?{params}"
    ZOHO_BASE_RECORDS_URL = "https://crm.zoho.com/crm/private/json/{module}/{method}?{params}"
    INITIAL_FROM_INDEX = 1
    MAX_RECORD_COUNT = 200

    allowed_domains = ["zoho.com"]
    json_data = None
    name = "zoho"
    response = None
    temp_dirs = list()

    def __init__(self, *args, **kwargs):
        super(ModuleSpider, self).__init__(*args, **kwargs)
        # Set starting timestamp
        self.timestamp = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
        self.timestamp_concatenated = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
        self.start_urls = [self.get_modules_url()]

    # Override from_crawler to properly pass Settings instance for use during __init__
    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings
        return cls(settings=settings)

    # Get modules formatted URL.
    def get_modules_url(self):
        params = {'authtoken': self.settings.get('ZOHO_CRM_AUTH_TOKEN'),
                  'scrope': 'crmapi'}
        return self.ZOHO_BASE_MODULES_URL.format(params=urlencode(params))

    # Get records formatted URL with pagination.
    def get_records_url(self, module, from_index, method='getRecords'):
        params = {'authtoken': self.settings.get('ZOHO_CRM_AUTH_TOKEN'),
                  'scrope': 'crmapi',
                  'fromIndex': from_index,
                  'toIndex': self.to_index(from_index)}
        if self.settings.get('ZOHO_LAST_MODIFIED_TIME'):
            params['lastModifiedTime'] = self.settings.get('ZOHO_LAST_MODIFIED_TIME')
        return self.ZOHO_BASE_RECORDS_URL.format(module=module,
                                                 method=method,
                                                 params=urlencode(params))

    # Determine if API indicated data is missing (empty DB table or query)
    def has_data(self, data_type='record'):
        if data_type == 'record':
            try:
                self.json_data['response']['nodata']
            except KeyError:
                return True
            else:
                logging.debug('No data was found matching query, url: {0}.'.format(self.response.url))
                return False
        elif data_type == 'deleted_record':
            try:
                if type(self.json_data['response']['result']['DeletedIDs']) is bool and self.json_data['response']['result']['DeletedIDs']:
                    return False
            except KeyError:
                logging.debug('No data was found matching query, url: {0}.'.format(self.response.url))
                return False
            else:
                return True

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

    # Determine if passed `module_name` is in settings whitelist (if altered).
    def is_module_allowed(self, module_name):
        modules = self.settings.get('ZOHO_MODULE_WHITELIST')
        if modules is None:
            return True
        elif type(modules) is str:
            if (modules.upper() == 'ALL') or modules == module_name:
                return True
        elif type(modules) is list:
            for module in modules:
                if module.upper() == 'ALL' or module == module_name:
                    return True
        return False

    # Initial parse to retrieve `Module` data.
    def parse(self, response):
        self.response = response
        data = json.loads(response.body.decode())

        for row in data['response']['result']['row']:
            module = row['content']
            # Ensure module is on approved whitelist
            if self.is_module_allowed(module):
                # Get deleted records for module
                deleted_records_url = self.get_records_url(module, self.INITIAL_FROM_INDEX, 'getDeletedRecordIds')
                yield scrapy.Request(deleted_records_url,
                                     meta={'module': module,
                                           'from_index': self.INITIAL_FROM_INDEX},
                                     callback=self.get_deleted_records)
                # Get record content for module
                records_url = self.get_records_url(module, self.INITIAL_FROM_INDEX)
                yield scrapy.Request(records_url,
                                     meta={'module': module,
                                           'from_index': self.INITIAL_FROM_INDEX},
                                     callback=self.get_records)

    # Secondary parse for each `Module` to retrieve deleted `Records` and output to feed
    def get_deleted_records(self, response):
        # TODO: Detect most recent execution date/time from either S3 timestamped directory or provided user setting
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
        if not self.has_data(data_type='deleted_record'):
            return

        # Verify JSON is valid
        if not self.is_json_valid():
            return

        logging.info('Deleted Record data retrieved for module: {0}, url: {1}'.format(module, self.response.url))
        if self.json_data['response']['result']['DeletedIDs']:
            id_list = [i.strip() for i in self.json_data['response']['result']['DeletedIDs'].split(',')]
            for ID in id_list:
                record = Record()
                record['module'] = module
                record['id'] = ID
                yield record

        # Generate next paginated URL
        from_index = response.meta['from_index']
        next_from_index = self.MAX_RECORD_COUNT + from_index
        next_url = self.get_records_url(module, next_from_index, 'getDeletedRecordIds')
        # Skip if output record maximum is exceeded
        if self.settings.get('OUTPUT_MAXIMUM_RECORDS') and next_from_index > self.settings.get(
                'OUTPUT_MAXIMUM_RECORDS'):
            return
        # Parse record content for each module
        yield scrapy.Request(next_url,
                             meta={'module': module,
                                   'from_index': next_from_index},
                             callback=self.get_deleted_records)

    # Secondary parse for each `Module` to retrieve `Records` and output to feed
    def get_records(self, response):
        # TODO: Detect most recent execution date/time from either S3 timestamped directory or provided user setting
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
                             callback=self.get_records)

    # Calculate the `to_index` for pagination
    def to_index(self, from_index):
        return from_index + self.MAX_RECORD_COUNT - 1
