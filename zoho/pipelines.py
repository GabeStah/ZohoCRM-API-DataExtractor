import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter
import tempfile
from zoho.split_file import SplitFile
from zoho.zoho_s3 import ZohoS3


class MultiRecordPipeline(object):
    """Pipeline used to generate exporters and create local files prior to splitting and uploading.

    :param object: Necessary extension as a Pipeline class.
    :type object: object
    """
    exporters = dict()
    files = dict()
    spider = None

    def __init__(self):
        """Initializes `MultiRecordPipeline while also calling `spider_opened` and `spider_closed` methods."""
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    def spider_opened(self, spider):
        """Required for inheritance and used to assign the `scrapy.Spider` instance to `self.spider` for later use.

        :param spider: `scrapy.Spider` in use by the current pipeline.
        :type spider: scrapy.Spider
        :return: Nothing
        :rtype: None
        """
        self.spider = spider

    def spider_closed(self, spider):
        """During closing process, finishe all exporters, close files, split files, and upload files.

        :param spider: `scrapy.Spider` in use by the current pipeline.
        :type spider: scrapy.Spider
        :return: Nothing
        :rtype: None
        """
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

        # Split temporary files into appropriate sizes
        self.split_files()

        # Upload
        self.upload_files()

    def create_exporter(self, name, file_type='json'):
        """Create the exporter (and file) based on the passed `name` parameter, typically the `Module` being parsed.

        :param name: Zoho CRM `Module` `name` that is parsed (e.g. Contacts, Leads, etc).
        :type name: str
        :param file_type: The desired file extension (default: json).
        :type file_type: str
        :return: Nothing
        :rtype: None
        """
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
        """Determines if the passed `exporter` name is already active (created), ensuring duplicates aren't created.

        :param exporter: Name of the exporter.
        :type exporter: str
        :return: Is the passed exporter name already in the active list.
        :rtype: bool
        """
        return exporter in set(self.exporters.keys())

    def is_file_active(self, file):
        """Determines if the passed `file` name is already active (created), ensuring duplicates aren't created.

        :param exporter: Name of the file.
        :type exporter: str
        :return: Is the passed file name already in the active list.
        :rtype: bool
        """
        return file in set(self.files.values())

    def process_item(self, item, spider):
        """Handles all processing of generated `zoho.items.Record` items (overriding `scrapy.Item`).

        Based on the `module` field passed along with the item, an exporter is created (if necessary), then the
        exporter is called and the `.export_item` method initiates the export process.

        :param item: The item containing all parsed data for this `Record`. Overrides `scrapy.Item`.
        :type item: zoho.items.Record
        :param spider: The `scrapy.Spider` which obtained this `Record`.
        :type spider: scrapy.Spider
        :return: As required by inheritence, the `zoho.items.Record` is returned after processing.
        :rtype: zoho.items.Record
        """
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
        """Splits all downloaded files into smaller, iterative chunked files, if necessary.

        Every temporary directory is looped, then all generated files within temp directories.  For each file found,
        the `zoho.split_file.SplitFile` class is instanced, which handles actual splitting procedures.

        A timestamped directory is generated to house all split files, which is also placed inside the
        `LOCAL_OUTPUT_DIRECTORY`, if specified.

        :return: Nothing
        :rtype: None
        """
        # Loop through temporary directories
        for temp_dir in self.spider.temp_dirs:
            for root, dirs, files in os.walk(temp_dir.name):
                # Loop through all files in each directory (to be safe, though should be one file per)
                for file_path in files:
                    file_name, extension = os.path.splitext(os.path.basename(file_path))
                    # Split file into smaller chunks
                    SplitFile(path=os.path.join(root, file_path),
                              lines=self.spider.settings.get('OUTPUT_LINES_PER_FILE'),
                              dest_dir=os.path.join(self.spider.settings.get('LOCAL_OUTPUT_DIRECTORY'),
                                                    self.spider.timestamp_concatenated,
                                                    file_name))

    def upload_files(self):
        """Instantiates the `zoho.zoho_s3.ZohoS3` class and attempts to upload all files in output directory.

        :return: Nothing
        :rtype: None
        """
        # Initialize S3
        zoho_s3 = ZohoS3(self.spider)
        # Upload files
        for root, dirs, files in os.walk(os.path.join(self.spider.settings.get('LOCAL_OUTPUT_DIRECTORY'),
                                                      self.spider.timestamp_concatenated)):
            for file_path in files:
                zoho_s3.upload(os.path.join(root, file_path),
                               os.path.join(root, file_path))
