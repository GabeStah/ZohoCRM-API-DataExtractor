# -*- coding: utf-8 -*-

# Scrapy settings for zoho project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
import os

# ---------------------
# BEGIN CUSTOM SETTINGS
# ---------------------
# AWS access key ID.  Can be specified directly as a string or indirectly as environmental variable.
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
# AWS secret access key.  Can be specified directly as a string or indirectly as environmental variable.
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# Name of AWS S3 bucket to export to.
AWS_BUCKET_NAME = 'zoho-crm-api-dev-2'
# Parent directory for all split export files to be stored AFTER split and upload.
LOCAL_OUTPUT_DIRECTORY = 'exports'
# Type of file to output.
OUTPUT_FILE_TYPE = 'json'
# Number of lines (maximum) per generated file before a new file is created and uploaded.  (default: 1000)
OUTPUT_LINES_PER_FILE = 1000
# Max requested records per `Module` (default: None -- Returns all records)
OUTPUT_MAXIMUM_RECORDS = 750
# S3 Transfer Config -- See: http://boto3.readthedocs.io/en/latest/_modules/boto3/s3/transfer.html
S3_NUM_DOWNLOAD_ATTEMPTS = 10
S3_MAX_CONCURRENCY = 10
S3_MULTIPART_CHUNKSIZE = 8 * 1024 * 1024
S3_MULTIPART_THRESHOLD = 8 * 1024 * 1024
# Zoho CRM authentication token.  Can be specified directly as a string or indirectly as environmental variable.
ZOHO_CRM_AUTH_TOKEN = os.getenv('ZOHO_CRM_AUTH_TOKEN')
# Creates an additional extra export 'module' and value of the Zoho CRM Module (default: False).
ZOHO_INCLUDE_MODULE_NAME = False
# API requests will only retrieve data created or modified after this time (default: None -- Returns all records)
# STRING FORMAT: '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()) e.g. '2016-07-11 00:00:00'
ZOHO_LAST_MODIFIED_TIME = None
# Determines which modules should be parsed (Default: None or 'ALL' -- Returns all records for all valid modules)
ZOHO_MODULE_WHITELIST = ['Contacts', 'Leads']
# ---------------------
# END CUSTOM SETTINGS
# ---------------------

BOT_NAME = 'zoho'

SPIDER_MODULES = ['zoho.spiders']
NEWSPIDER_MODULE = 'zoho.spiders'

LOG_LEVEL = 'INFO'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'zoho (+http://www.yourdomain.com)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY = 3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
#CONCURRENT_REQUESTS_PER_IP = 16

# Disable cookies (enabled by default)
#COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED = False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'zoho.middlewares.MyCustomSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'zoho.middlewares.MyCustomDownloaderMiddleware': 543,
#}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
ITEM_PIPELINES = {
    'zoho.pipelines.MultiRecordPipeline': 300,
}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
#AUTOTHROTTLE_ENABLED = True
# The initial download delay
#AUTOTHROTTLE_START_DELAY = 5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY = 60
# The average number of requests Scrapy should be sending in parallel to
# each remote server
#AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED = True
#HTTPCACHE_EXPIRATION_SECS = 0
#HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'
