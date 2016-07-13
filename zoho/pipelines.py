# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter


class MultiRecordPipeline(object):
    files = dict()
    exporter_file_type = 'json'
    exporters = dict()

    def __init__(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)

    # Necessary for inheritance
    def spider_opened(self, spider):
        return

    # During closing process, finish all exporters and close all files
    def spider_closed(self, spider):
        [e.finish_exporting() for e in self.exporters.values()]
        [f.close() for f in self.files.values()]

    def is_exporter_active(self, exporter):
        return exporter in set(self.exporters.keys())

    def is_file_active(self, file):
        return file in set(self.files.values())

    # Create the exporter (and file) based on the `name` parameter
    def create_exporter(self, name):
        # Ensure exporter hasn't been generated
        if self.is_exporter_active(name):
            return

        # create file: ModuleName.json
        self.files[name] = open(name + '.' + self.exporter_file_type, 'w+b')
        # create exporter
        self.exporters[name] = JsonLinesItemExporter(self.files[name])
        # begin export
        self.exporters[name].start_exporting()

    def process_item(self, item, spider):
        # Exporters are named after modules
        exporter_name = item['module']
        self.create_exporter(exporter_name)

        if self.is_exporter_active(exporter_name):
            # Call the base `export_item` method for parent exporter type
            self.exporters[exporter_name].export_item(item)
        return item