# ZohoCRM-API-DataExtractor
Extracts module and record information from the [Zoho CRM API](https://www.zoho.com/crm/help/api/) via
Python/[scrapy](http://scrapy.org/) and uploads exported data to [Amazon S3](https://aws.amazon.com/s3/).

## Requirements

* [Scrapy 1.1.0](http://scrapy.org/) or greater.
* [Boto3 1.3.1](https://pypi.python.org/pypi/boto3/) or greater.
* [Zoho CRM](https://www.zoho.com/crm/) account with API access and valid [AuthToken](https://www.zoho.com/crm/help/api/using-authentication-token.html).
* [Amazon S3](https://aws.amazon.com/s3/) account for storing exported files, with a valid [Access Key ID and Secret Access Key](http://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSGettingStartedGuide/AWSCredentials.html).

## Usage

1. Add appropriate authentication tokens for `Zoho CRM` and `S3` to the 
`settings.py` file.  Settings values can either be strings or references 
to environment variables if preferred.  Settings that require a change are: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `ZOHO_CRM_AUTH_TOKEN`.  
2. Now simply execute the scrapy spider from the command line (`scrapy crawl zoho`) or, alternatively, run the `execute_zoho.py` Python script.

All custom `Settings` are documented to explain their purpose.

## Output

Upon execution, the `zoho` spider will connect to the Zoho CRM API and extract all `Modules`. For each `Module`, the [`getRecords`](https://www.zoho.com/crm/help/api/getrecords.html) 
method is called and retrieves all valid records (in batches of 200 per request).  The same process occurs for all modules to retrieve the deleted records 
via the [`getDeletedRecordIds`](https://www.zoho.com/crm/help/api/getdeletedrecordids.html) method.  All extracted records are stored in `Newline Delimited JSON` files, with names representing 
the `Module` of the underlying record types.  These files are stored in temporary directories on the local system.
 
Once all data is extracted from `Zoho CRM`, files are split up into smaller chunks (if necessary) and placed in a timestamped parent directory within the `LOCAL_OUTPUT_DIRECTORY` directory. 
Files are split into chunks based on the maximum number of lines per file, as specified by `OUTPUT_LINES_PER_FILE`.

Finally, once all files are split as necessary, the entire batch of files are uploaded to the `Amazon S3` bucket specified by `AWS_BUCKET_NAME` (if the bucket doesn't exist, it is created).

## Customisation

In some cases, it may be desired to limit the `Zoho CRM` data that is extracted or the exported files intended to be uploaded to `Amazon S3`.  Below are a few configurable `Settings` to allow this.

### ZOHO_MAX_RECORDS_PER_MODULE

Due to the limit on API calls `Zoho CRM` allows in a day, it may be worthwhile to limit the number of records returned by a crawl.  Or if all records are desired, set the value to `None`.

### ZOHO_MODULE_WHITELIST

If you wish to query only specific `Modules`. the `Module` `names` can be listed in this setting.  
Note: Not all `Modules` can be [accessed using the API](https://www.zoho.com/crm/help/api/modules-fields.html), so even if you manually specify such a `Module` `name` in this list, it will be 
ignored if the API cannot access it.  Setting this to `None` or `'ALL'` ensures all `Modules` are parsed.
 
### ZOHO_LAST_MODIFIED_TIME

If you wish to get __only__ `Records` which have been created or modified since a particular date/time, enter that value in this setting.  If unspecified, all records in the system are returned.