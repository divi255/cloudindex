# Cloud Index

Indexes Google Cloud Platform / Amazon S3 buckets into JSON.

## Installation

```
pip3 install cloudindex

# additionally, for GCS
pip3 install google.cloud.storage

# additionally, for S3
pip3 install boto3
```

## Authentication

* To index your bucket, you need to create GCP servece account
  (permissions required: Storage Legacy Bucket Reader & Storage Object
  Viewer) and then create a key for it. Put a path to keyfile to
  GOOGLE_APPLICATION_CREDENTIALS env variable or specify it in application
  command line params.

* For Amazon S3 JSON key is also required. Amazon doesn't supply JSON keys,
  create it manually:

    {
        "aws_access_key_id": "KEYID",
        "aws_secret_access_key": "SECRETKEY"
    }

* Additionally, for S3 you can specify in JSON fields *region_name* and
  *endpoint_url*, e.g. to connect to Digital Ocean Spaces:

    {
        "aws_access_key_id": "KEYID",
        "aws_secret_access_key": "SECRETKEY",
        "region_name": "nyc3",
        "endpoint_url": "https://nyc3.digitaloceanspaces.com"
    }
    
* Don't forget to set 600 permission on all key files you have.

* If started on Google Cloud / Amazon EC2, key file may be omitted

## Usage

### CLI tool

```
usage: cloud-index [-h] [--version] [-p DIR] [-k FILE] [-s TYPE] [-r]
                   [-x FILE] [-T DIR] [--fetch-meta] [-c] [-M FILE:field]
                   BUCKET

Cloud Storage indexer

positional arguments:
  BUCKET                bucket to index

optional arguments:
  -h, --help            show this help message and exit
  --version             Print version and exit
  -p DIR, --prefix DIR  Bucket object prefix (default: /)
  -k FILE, --key-file FILE
                        Get CS key from file (default for gcs: from
                        GOOGLE_APPLICATION_CREDENTIALS environment variable)
  -s TYPE, --cloud-storage TYPE
                        Cloud storage type: gcs for Google, s3 for Amazon S3
                        and compatible (default: gcs)
  -r, --recursive       Recursively include "subdirectories" and their objects
  -x FILE, --exclude FILE
                        Files (masks) to exclude)
  -T DIR, --time-format DIR
                        Time format (default: %Y-%m-%d %H:%M)
  --fetch-meta          Fetch custom metadata (for S3), for GCS meta data is
                        always included
  -c, --checksums       Get checksums from md5sums, sha1sums and sha256sums
  -M FILE:field, --meta-file FILE:field
                        Additional "<info> <file>" file, e.g. SSL certs
                        fingerprints etc.
```

Option "-M" allows to include custom meta info, e.g. you can display
fingerprints of SSL certificates hosted in bucket if this data is stored (as
"FINGERPRINT FILENAME", one per line) in "FINGERPRINTS" (case insensitive)
file:

   cloud-index ..... -M FINGERPRINTS:fingerprint <BUCKET>

If option "-c" is given to indexer, additional file attributes "md5", "sha1"
and "sha256" appear. Indexer will update them if files "md5sums", "sha1sums" or
"sha256sums" (case doesn't matter) are present in current directory. File
format is standard: "CHECKSUM  FILENAME" (one per line). This option is
actually equal to

    cloud-index ..... -M sha256sums:sha256 -M md5sums:md5 -M sha1sums:sha1

### Library

Refer to cloudindex library pydoc for the functions and args.

## Nuts and bolts

* As buckets don't have real folders, sometimes it can't get a proper
  modification date or calculate folder size.

* All object meta variables are indexed as well. If object has checksum meta
  data ("md5"/"sha1"/"sha256") and "-c" option is used, meta data value has
  higher priority than value from uploaded old-style meta info files.

* If meta variable called "local-creation-time" is set, object creation
  date/time are overriden with it. You may set it e.g. when copying file to
  bucket:

```
gsutil -h "x-goog-meta-local-creation-time:2020-02-15 23:51:00" ....
```
