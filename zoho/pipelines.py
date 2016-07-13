import os
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter
from zoho.zoho_s3 import ZohoS3


class MultiRecordPipeline(object):
    files = dict()
    exporters = dict()

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    # Necessary for inheritance
    def spider_opened(self, spider):
        pass

    # During closing process, finish all exporters and close all files
    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]
        # Initialize S3 output
        zoho_s3 = ZohoS3(spider)
        # Upload files
        for module, file in self.files.items():
            zoho_s3.upload(file.name, module + '/')
            # Delete temporary file
            # TODO: Verify correct deletion OR omit deletion entirely
            # Temporary removal due to process lock
            #os.remove(file.name)

    # Create the exporter (and file) based on the `name` parameter
    def create_exporter(self, name, file_type):
        # TODO: Exporters must be generated programmatically with incremental output file names
        # Ensure exporter hasn't been generated
        if self.is_exporter_active(name):
            return

        # create file: name.extension
        self.files[name] = open(name + '.' + file_type, 'w+b')
        # TODO: (Optional) Modify exporter class used based on file_type
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
        self.create_exporter(exporter_name, spider.settings.get('OUTPUT_FILE_TYPE'))

        if self.is_exporter_active(exporter_name):
            # Call the base `export_item` method for parent exporter type
            self.exporters[exporter_name].export_item(item)
        return item




