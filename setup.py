__version__ = '0.0.6'

import setuptools

with open('README.md', 'r') as fh:
    long_description = fh.read()

setuptools.setup(
    name='cloudindex',
    version=__version__,
    author='Sergei S.',
    author_email='s@makeitwork.cz',
    description='Cloud bucket indexer',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/divi255/cloud-index',
    packages=setuptools.find_packages(),
    license='MIT',
    install_requires=[
        'pyaltt2'  # google.cloud.storage or boto3
    ],
    scripts=['bin/cloud-index'],
    classifiers=('Programming Language :: Python :: 3',
                 'License :: OSI Approved :: MIT License', 'Topic :: Internet',
                 'Topic :: Utilities'),
)
