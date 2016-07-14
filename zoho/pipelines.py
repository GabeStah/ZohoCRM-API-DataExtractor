import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter
import tempfile
from zoho.split_file import SplitFile
from zoho.zoho_s3 import ZohoS3


class MultiRecordPipeline(object):
    exporters = dict()
    files = dict()
    spider = None

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    # Necessary for inheritance
    def spider_opened(self, spider):
        self.spider = spider

    # During closing process, finish all exporters and close all files
    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

        # Split temporary files into appropriate sizes
        self.split_files()

        # Upload
        self.upload_files()

    # Create the exporter (and file) based on the `name` parameter
    def create_exporter(self, name, file_type):
        # Ensure exporter hasn't been generated
        if self.is_exporter_active(name):
            return

        # Create temporary directory for each file to avoid process lock
        temp_dir = tempfile.TemporaryDirectory()
        # Track for later retrieval when splitting
        self.spider.temp_dirs.append(temp_dir)
        file_name = os.path.join(temp_dir.name, name + '.' + file_type)
        # Add to active files list
        self.files[name] = open(file_name, 'w+b')
        # create exporter
        self.exporters[name] = JsonLinesItemExporter(self.files[name])
        # begin export
        self.exporters[name].start_exporting()

    def is_exporter_active(self, exporter):
        return exporter in set(self.exporters.keys())

    def is_file_active(self, file):
        return file in set(self.files.values())

    def process_item(self, item, spider):
        # Exporters are named after modules
        exporter_name = item['module']

        # Deleted item
        if len(item._values) <= 2 and item['id']:
            exporter_name += '-Deleted'
        self.create_exporter(exporter_name, spider.settings.get('OUTPUT_FILE_TYPE'))

        # Remove module from export field unless setting requests it
        if not spider.settings.get('ZOHO_INCLUDE_MODULE_NAME'):
            del item['module']

        if self.is_exporter_active(exporter_name):
            # Call the base `export_item` method for parent exporter type
            self.exporters[exporter_name].export_item(item)
        return item

    def split_files(self):
        # Loop through temporary directories
        for temp_dir in self.spider.temp_dirs:
            for root, dirs, files in os.walk(temp_dir.name):
                # Loop through all files in each directory (to be safe, though should be one file per)
                for file_path in files:
                    file_name, extension = os.path.splitext(os.path.basename(file_path))
                    # Split file into smaller chunks
                    SplitFile(path=os.path.join(root, file_path),
                              lines=self.spider.settings.get('OUTPUT_LINES_PER_FILE'),
                              destination=os.path.join(self.spider.settings.get('LOCAL_OUTPUT_DIRECTORY'),
                                                       self.spider.timestamp_concatenated,
                                                       file_name))

    # Instantiates S3 class and uploads all files in temp directory
    def upload_files(self):
        # Initialize S3
        zoho_s3 = ZohoS3(self.spider)
        # Upload files
        for root, dirs, files in os.walk(os.path.join(self.spider.settings.get('LOCAL_OUTPUT_DIRECTORY'),
                                                      self.spider.timestamp_concatenated)):
            for file_path in files:
                zoho_s3.upload(os.path.join(root, file_path),
                               os.path.join(root, file_path))
