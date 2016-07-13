from itertools import chain, islice
import os


class SplitFile:

    def __init__(self, path=None, lines=250, destination=''):
        if path is None:
            return
        self.base_name = os.path.basename(path)
        self.destination = destination
        self.file_name, self.extension = os.path.splitext(os.path.basename(path))
        self.lines = lines
        self.path = path

        # Initiate split
        self.split()

    @staticmethod
    def chunk(iterable, line):
        iterable = iter(iterable)
        while True:
            yield chain([next(iterable)], islice(iterable, line-1))

    def split(self):
        with open(self.path) as original:
            for count, lines in enumerate(self.chunk(original, self.lines)):
                # Format new split file name
                split_file_name = '{0}-{1}{2}'.format(os.path.join(self.destination, self.file_name),
                                                      count,
                                                      self.extension)
                split_dir = os.path.dirname(split_file_name)
                # Ensure split dir is valid and exists
                if split_dir and split_dir != '':
                    os.makedirs(split_dir, exist_ok=True)
                # write split file lines
                with open(split_file_name, 'w+') as split_file:
                    split_file.writelines(lines)
