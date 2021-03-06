from setuptools import setup, find_packages

setup(
    name='ZohoCRM',
    version='1.0.0',
    packages=find_packages(),

    install_requires=[
        'boto3',
        'botocore',
        'scrapy',
    ],

    url='',
    license='',
    author='Gabe Wyatt',
    author_email='gabe@gabewyatt.com',
    description='Extract Zoho CRM API data and upload to AWS S3.'
)
