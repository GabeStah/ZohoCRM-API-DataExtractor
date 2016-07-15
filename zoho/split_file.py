from itertools import chain, islice
import os


class SplitFile:
    """Used to easily split larger output files into smaller, more manageable sets of equally-sized files.  Split files
    are numerically incremented and are processed based on the maximum number of `lines` per file."""

    def __init__(self, path=None, lines=1000, dest_dir=''):
        """Initializes the `SplitFile` class and assigns important values to class variables.

        :param path: The full `path` to the file intended to be split.
        :type path: str or None
        :param lines: The maximum number of lines for each split file (optional, default: 1000).
        :type lines: int
        :param dest_dir: Desired destination directory in which to place split files (optional, default: '').
        :type dest_dir: str or None
        """
        if path is None:
            return
        self.base_name = os.path.basename(path)
        self.dest_dir = dest_dir
        self.file_name, self.extension = os.path.splitext(os.path.basename(path))
        self.lines = lines
        self.path = path

        # Initiate split
        self.split()

    @staticmethod
    def chunk(iterable, line):
        """Chains together the iterable lines in the source file until the file is "empty".

        :param iterable: Iterable set of lines.
        :type iterable: TextIOWrapper
        :param line: Current line in enumerated line set.
        :type line: int
        :return: Yielded `Chain` to continue iterating through lines.
        :rtype: itertools.Chain
        """
        iterable = iter(iterable)
        while True:
            yield chain([next(iterable)], islice(iterable, line-1))

    def split(self):
        """Splits all exported files stored in temporary directories into smaller chunks based on maximum `self.lines`
        size.

        :return: Nothing
        :rtype: None
        """
        with open(self.path) as original:
            for count, lines in enumerate(self.chunk(original, self.lines)):
                # Format new split file name
                split_file_name = '{0}-{1}{2}'.format(os.path.join(self.dest_dir, self.file_name),
                                                      count,
                                                      self.extension)
                split_dir = os.path.dirname(split_file_name)
                # Ensure split dir is valid and exists
                if split_dir and split_dir != '':
                    os.makedirs(split_dir, exist_ok=True)
                # write split file lines
                with open(split_file_name, 'w+') as split_file:
                    split_file.writelines(lines)
