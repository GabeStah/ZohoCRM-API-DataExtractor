import boto3
from boto3.s3.transfer import S3Transfer, TransferConfig
import botocore
import logging

RESOURCE_TYPE = 's3'


class ZohoS3:
    """Handles all connections with Amazon S3 services, authenticating a session, creating a bucket (if necessary),
    and uploading all split files.

    Hooks into the `boto3` and `botocore` modules for `Session`, `Resource`, `TransferConfig`, and `S3Transfer`.
    """
    bucket_name = None
    resource = None
    spider = None

    def __init__(self, spider):
        """Initializes the `ZohoS3` class amd generates a `boto3.Session`, `resource.meta.client`, and S3 bucket
        (if needed).

        Appropriate errors are called if connection fails at any point in the chain.

        :param spider: `scrapy.Spider` reference for use throughout the class instance.
        :type spider: scrapy.Spider
        """
        # Assign spider
        self.spider = spider
        # Assign bucket name
        self.bucket_name = spider.settings.get('AWS_BUCKET_NAME')
        if self.bucket_name is None:
            logging.error('ZohoS3 requires valid AWS_BUCKET_NAME setting in scrapy config.')
            return

        # Create session object
        try:
            session = boto3.Session(
                aws_access_key_id=spider.settings.get('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=spider.settings.get('AWS_SECRET_ACCESS_KEY')
            )
        except botocore.exceptions.ClientError:
            logging.error('Unable to create S3 session.')

        # Connect to resource
        try:
            self.resource = session.resource(RESOURCE_TYPE)
        except botocore.exceptions.ClientError:
            logging.error('Unable get AWS resource ({0}).'.format(RESOURCE_TYPE))

        # Get client
        self.client = self.resource.meta.client

        # Get bucket
        self.bucket = self.get_bucket()

    def bucket_exists(self):
        """Determines if the specified bucket name in `AWS_BUCKET_NAME` already exists in S3.

        :return: Does the bucket exist.
        :rtype: bool
        """
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucket_name)
        except botocore.exceptions.ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                return False
        return True

    def create_bucket(self):
        """Creates a new bucket from the `AWS_BUCKET_NAME`.  `self.bucket_exists()` must be called first to verify
        that a new bucket can and should be created.

        :return: Nothing
        :rtype: None
        """
        # Generate bucket
        self.resource.create_bucket(Bucket=self.bucket_name)

    def format_remote_path(self, path):
        """Ugly hack for proper AWS S3 path formatting.

        Due to underlying operating system, when using the Zoho CRM API crawler module on Windows, it may be
        necessary to perform cleanup on the paths.

        :param path: Path to properly format.
        :type path: str
        :return: Formatted path.
        :rtype: str
        """
        output_dir = self.spider.settings.get('LOCAL_OUTPUT_DIRECTORY')
        remote_path = path.replace(output_dir, '').replace('\\', '/')
        if remote_path.startswith('/'):
            remote_path = remote_path[1:]
        return remote_path

    def get_bucket(self):
        """Creates a new bucket (if necessary), then retrieve valid bucket `resource.Bucket` instance for use elsewhere.

        :return: Active `resource.Bucket`.
        :rtype: resource.Bucket
        """
        # if exists, create
        if not self.bucket_exists():
            self.create_bucket()
        return self.resource.Bucket(self.bucket_name)

    def upload(self, local_path, remote_path=''):
        """Uploads the specified local file to Amazon S3.

        Utilizes numerous `AWS_` settings to handle transfer limitations and speed.  See `settings.py` for details.

        :param local_path: Full path to the local file to be uploaded.
        :type local_path: str
        :param remote_path: Full remote path (within the bucket) to place the file in on S3 (optional, default: '').
        :type remote_path: str or None
        :return: Nothing
        :rtype: None
        """
        try:
            config = TransferConfig(
                num_download_attempts=self.spider.settings.get('S3_NUM_DOWNLOAD_ATTEMPTS'),
                max_concurrency=self.spider.settings.get('S3_MAX_CONCURRENCY'),
                multipart_chunksize=self.spider.settings.get('S3_MULTIPART_CHUNKSIZE'),
                multipart_threshold=self.spider.settings.get('S3_MULTIPART_THRESHOLD')
            )
            transfer = S3Transfer(self.client, config)
            transfer.upload_file(local_path,
                                 self.bucket_name,
                                 self.format_remote_path(remote_path))

        except botocore.exceptions.ClientError as e:
            logging.error('Unable to upload file {0} from path {1}'.format(local_path, remote_path))
