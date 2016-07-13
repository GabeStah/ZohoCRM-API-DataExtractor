import boto3
import botocore
import logging

RESOURCE_TYPE = 's3'


class ZohoS3:
    bucket = None
    resource = None
    spider = None

    def __init__(self, spider):
        # Assign spider
        self.spider = spider
        # Assign bucket name
        self.bucket = spider.settings.get('AWS_BUCKET_NAME')
        if self.bucket is None:
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

        # Create bucket
        self.create_bucket()

    def bucket_exists(self):
        try:
            self.resource.meta.client.head_bucket(Bucket=self.bucket)
        except botocore.exceptions.ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                return False
        return True

    def create_bucket(self):
        # If bucket exists, exit
        if self.bucket_exists():
            return

        # Generate bucket
        self.resource.create_bucket(Bucket=self.bucket)

    def upload(self, local_path, remote_path=''):
        try:
            self.resource.Object(self.bucket, remote_path + local_path).put(Body=open(local_path, 'rb'))
        except botocore.exceptions.ClientError as e:
            logging.error('Unable to upload file {0} from path {1}'.format(local_path, remote_path))
