import datetime
import json
import logging
import scrapy
from urllib.parse import urlencode

from zoho.items import Record


class ZohoSpider(scrapy.Spider):
    """Core scrapy `Spider` that crawls Zoho CRM API for Module and associated new/modified Records.

    Overrides `scrapy.Spider` - Used for generating all crawls necessary for ZohoCRM to function.

    :param scrapy.Spider: Extended `scrapy.Spider`.
    :type scrapy.Spider: scrapy.Spider
    """
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
        """Initializes `ZohoSpider`.

        :param args: Variable `args`.
        :type args: object
        :param kwargs: Variable `kwargs`.
        :type kwargs: object
        """
        super(ZohoSpider, self).__init__(*args, **kwargs)
        # Set starting timestamp
        self.timestamp = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
        self.timestamp_concatenated = '{:%Y-%m-%d_%H-%M-%S}'.format(datetime.datetime.now())
        self.start_urls = [self.get_modules_url()]

    # Override from_crawler to properly pass Settings instance for use during __init__
    @classmethod
    def from_crawler(cls, crawler):
        """Overrides `from_crawler` method to allow for Settings class instance to be used during `self.__init__`.

        :param crawler: Extended `scrapy.Crawler`.
        :type crawler: scrapy.Crawler
        :return: Extended `scrapy.Spider` instance with passed in `scrapy.Settings`.
        :rtype: scrapy.Spider
        """
        settings = crawler.settings
        return cls(settings=settings)

    # Get modules formatted URL.
    def get_modules_url(self):
        """Constructs the formatted URL for the Zoho CRM Modules API call.

        :return: Full, authenticated URL for getModules Zoho API.
        :rtype: str
        """
        params = {'authtoken': self.settings.get('ZOHO_CRM_AUTH_TOKEN'),
                  'scope': 'crmapi'}
        return self.ZOHO_BASE_MODULES_URL.format(params=urlencode(params))

    # Get records formatted URL with pagination.
    def get_records_url(self, module, from_index, method='getRecords'):
        """Constructs the formatted URL for the Zoho CRM getRecords and getDeletedRecordIds API calls.

        :param module: Zoho CRM Module name (e.g. Contacts, Leads, etc).
        :type module: str
        :param from_index: Initial record index to retrieve with this URL instance.
        :type from_index: int
        :param method: Which API method to request (getRecords vs getDeletedRecordIds).
        :type method: str
        :return: Full, authenticated URL for the appropriate getRecords or getDeletedRecordIds Zoho API request.
        :rtype: str
        """
        params = {'authtoken': self.settings.get('ZOHO_CRM_AUTH_TOKEN'),
                  'scope': 'crmapi',
                  'fromIndex': from_index,
                  'toIndex': self.to_index(from_index)}
        if self.settings.get('ZOHO_LAST_MODIFIED_TIME'):
            params['lastModifiedTime'] = self.settings.get('ZOHO_LAST_MODIFIED_TIME')
        return self.ZOHO_BASE_RECORDS_URL.format(module=module,
                                                 method=method,
                                                 params=urlencode(params))

    #
    def has_data(self, data_type='record'):
        """Determine if API response has indicated that data present or missing (empty DB table or query).

        :param data_type: Type of data object API call to examine (e.g. getRecords vs getDeletedRecordIds).
        :type data_type: str
        :return: Indicates whether data from API call present.
        :rtype: bool
        """
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

    def is_json_valid(self):
        """Determine if API response indicated if JSON was valid or an error occurred.

        :return: Is response JSON is valid or not.
        :rtype: bool
        """
        # Error in response
        try:
            self.json_data['response']['error']
        except KeyError:
            return True
        else:
            logging.debug('JSON is invalid, url: {0}.'.format(self.response.url))
            return False

    @staticmethod
    def is_response_valid(response):
        """Determine if passed `response` object is valid.

        :param response: Response object obtained through scrapy crawl process.
        :type response: scrapy.http.response.Response
        :return: Is response object valid with a status of 200.
        :rtype: bool
        """
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

    def is_module_allowed(self, module_name):
        """Determine if passed `module_name` is in `ZOHO_MODULE_WHITELIST` (if applicable).

        :param module_name: Name of the Zoho CRM Module.
        :type module_name: str
        :return: Was `module_name` found in WHITELIST (or WHITELIST set to 'All' or None).
        :rtype: bool
        """
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

    def parse(self, response):
        """Primary parse method to retrieve Zoho CRM `Module` data.

        Overrides `scrapy.Spider`.  Uses the full list of obtained `Module` names and for each, generates
        `scrapy.Request` objects for both the getRecords and getDeletedRecordIds API calls.

        :param response: Response object obtained from scrapy's `Request`.
        :type response: scrapy.http.response.Response
        :return: Typically a new `scrapy.Request` that parses for `Records` or `DeletedRecords`.
        :rtype: `scrapy.Request` or None
        """
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

    def get_deleted_records(self, response):
        """Secondary parse for to retrieve all `DeletedRecords` via getDeletedRecordIds.

        Since Zoho API limits maximum index range to 200 records, this method often generates a callback to itself,
        parsing for the next set of 200 records, continuing until a `Response` with no data occurs.

        :param response: Response object obtained from scrapy's `Request`.
        :type response: scrapy.http.response.Response
        :return: Typically a new `scrapy.Request` that parses for the next set of `DeletedRecords`.
        :rtype: `scrapy.Request` or None
        """
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
        max_records = self.settings.get('ZOHO_MAX_RECORDS_PER_MODULE')
        # Skip if output record maximum is exceeded
        if max_records and next_from_index > max_records:
            return
        # Parse record content for each module
        yield scrapy.Request(next_url,
                             meta={'module': module,
                                   'from_index': next_from_index},
                             callback=self.get_deleted_records)

    def get_records(self, response):
        """Secondary parse for to retrieve all `Records` via getRecords.

        Since Zoho API limits maximum index range to 200 records, this method often generates a callback to itself,
        parsing for the next set of 200 records, continuing until a `Response` with no data occurs.

        :param response: Response object obtained from scrapy's `Request`.
        :type response: scrapy.http.response.Response
        :return: Typically a new `scrapy.Request` that parses for the next set of `Records`.
        :rtype: `scrapy.Request` or None
        """
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
        max_records = self.settings.get('ZOHO_MAX_RECORDS_PER_MODULE')
        # Skip if output record maximum is exceeded
        if max_records and next_from_index > max_records:
            return
        # Parse record content for each module
        yield scrapy.Request(next_url,
                             meta={'module': module,
                                   'from_index': next_from_index},
                             callback=self.get_records)

    def to_index(self, from_index):
        """Property to get the `to_index` value for upcoming Zoho CRM API calls.

        Read-only.

        :param from_index: The `from_index` value that is currently being used.
        :type from_index: int
        :return: The `to_index` value, incremented accordingly to obtain the most records per API call possible.
        :rtype: int
        """
        return from_index + self.MAX_RECORD_COUNT - 1
