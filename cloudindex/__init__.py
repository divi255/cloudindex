import os
import fnmatch
import pytz

from pyaltt2.converters import parse_date
from types import SimpleNamespace

__version__ = '0.0.6'

_object_field_map = {
    'gcs': {
        'name': 'name',
        'date': 'updated',
        'size': 'size'
    },
    's3': {
        'name': 'Key',
        'date': 'LastModified',
        'size': 'Size'
    }
}


def get_blob(o, cs='gcs'):
    if cs == 'gcs':
        return o.download_as_string().decode()
    elif cs == 's3':
        return client.get_object(Key=o['Key'],
                                 Bucket=bucket)['Body'].read().decode()
    else:
        return None


def make_index(bucket,
               key=None,
               prefix='/',
               exclude=[],
               time_format='%Y-%m-%d %H:%M',
               recursive=False,
               cs='gcs',
               fetch_meta=False,
               get_checksums=False,
               meta_files=[]):
    """
    Args:
        bucket: bucket to index
        key: keyfile for gcs, keyfile/dict for s3 or None to use default env.
        prefix: bucket prefix (default: /)
        exclude: list of exclude masks
        time_format: default: %Y-%m-%d %H:%M
        recursive: recursive indexing
        cs: cloud storage, gcs (default) or s3
        fetch_meta: fetch additional meta data (for s3)
        get_chesksums: get additional metadata from checksum files (md5sums,
            sha1sums, sha256sums)
        meta_files: list of extra "<info>  <file>" files, (FILE, field) tuples
    """

    metainfo = []
    metainfo_files = {}

    if get_checksums:
        metainfo_files = {
            'md5sums': 'md5',
            'sha1sums': 'sha1',
            'sha256sums': 'sha256'
        }
        metainfo = ['md5', 'sha1', 'sha256']

    if meta_files:
        for p in meta_files:
            f, i = p
            f = f.lower()
            if i not in metainfo:
                metainfo.append(i)
                if f in metainfo_files:
                    metainfo.remove(metainfo_files[f])
                metainfo_files[f] = i

    if metainfo:
        import re
        css_reg = re.compile('[\ \t]+')

    if prefix.endswith('/'):
        prefix = prefix[:-1]

    if prefix.startswith('/'):
        prefix = prefix[1:]

    structure = {}
    folder_info = {}

    def apply_metainfo_file(o, filename, foldername, ctype):
        key = ('/' + prefix if prefix else '/') + foldername
        sfile = get_blob(o)
        if not sfile: return
        sums = {}
        for l in (sfile.split('\n')):
            if l:
                try:
                    s, f = re.split(css_reg, l.strip())
                    sums[f] = s
                    # update files if we already have any
                    if key in structure:
                        l = structure.get(key)
                        for x in l:
                            if x['name'] == f:
                                x[ctype] = s
                except:
                    raise Exception('Parse error {}'.format(filename))
        folder_info.setdefault(key, {})[ctype] = sums

    def append_file(name,
                    size,
                    d=None,
                    folder='',
                    meta={},
                    update_info_only=False):
        key = (('/' + prefix +
                ('/' if folder else '')) if prefix else '/') + folder
        if not update_info_only:
            file_info = {
                'is_dir': False,
                'name': name,
                'size': size,
                'date': (d.strftime(time_format) if d else None)
            }
            file_info.update(meta)
            if metainfo:
                for c in metainfo:
                    if c not in file_info:
                        file_info[c] = None
                i = folder_info.get(key)
                if i:
                    for c in metainfo:
                        sums = i.get(c)
                        if sums and name in sums:
                            file_info[c] = sums[name]

            structure.setdefault(key, []).append(file_info)
        if d and key != '/': update_folder_info(key, d, size)

    def append_folder(folder):
        if folder.find('/') != -1:
            append_folder('/'.join(folder.split('/')[:-1]))
        parent = '/'.join(folder.split('/')[:-1])
        key = ('/' + prefix if prefix or not parent else '') + ('/' + parent if
                                                                parent else '')
        name = folder.split('/')[-1]
        try:
            min(filter(lambda el: el['name'] == name, structure.get(key, [])))
            return
        except:
            pass
        structure.setdefault(key, []).append({
            'is_dir': True,
            'name': name,
            'date': None,
            'size': None
        })

    def update_folder_info(folder, d, size):
        if folder.find('/') != -1 and folder != '/':
            update_folder_info('/'.join(folder.split('/')[:-1]), d, size)
        if folder not in folder_info:
            folder_info[folder] = {'d': d, 's': size}
        else:
            if 's' not in folder_info[folder]:
                folder_info[folder]['s'] = size
            else:
                folder_info[folder]['s'] += size
            if 'd' not in folder_info[folder]:
                folder_info[folder]['d'] = d
        n = folder.split('/')
        key = '/'.join(n[:-1])
        if not key: key = '/'
        foldername = n[-1]
        f = structure.get(key)
        if not f: return
        for l in f:
            if l['is_dir'] and l['name'] == foldername:
                if not l['date'] or folder_info.get(folder)['d'].replace(
                        tzinfo=None) < d.replace(tzinfo=None):
                    l['date'] = d.strftime(time_format)
                l['size'] = folder_info.get(folder)['s']
                break

    if cs == 'gcs':
        from google.cloud import storage
        client = storage.Client.from_service_account_json(
            key) if key else storage.Client()
        bucket = client.get_bucket(bucket)
        objects = bucket.list_blobs(prefix=prefix)
    elif cs == 's3':
        import boto3
        session = boto3.session.Session()
        if isinstance(key, str):
            with open(key) as fh:
                import json
                key = json.loads(fh.read())
        if isinstance(key, dict):
            client = session.client(
                's3',
                region_name=key.get('region_name'),
                endpoint_url=key.get('endpoint_url'),
                aws_access_key_id=key['aws_access_key_id'],
                aws_secret_access_key=key['aws_secret_access_key'])
        else:
            client = session.client('s3')
        try:
            objects = client.list_objects_v2(Bucket=bucket,
                                             Prefix=prefix,
                                             FetchOwner=False)['Contents']
        except KeyError:
            # empty bucket
            objects = []
    else:
        raise ValueError('cloud storage type unknown: {}'.format(cs))

    def format_object(o):
        out = SimpleNamespace()
        for k, v in _object_field_map[cs].items():
            if isinstance(o, dict):
                value = o[v]
            else:
                value = getattr(o, v)
            setattr(out, k, value)
        if cs == 'gcs':
            out.meta = o.metadata if o.metadata else {}
        elif fetch_meta:
            out.meta = {
                k[11:]: v
                for k, v in client.head_object(Bucket=bucket, Key=o['Key'])
                ['ResponseMetadata']['HTTPHeaders'].items()
                if k.startswith('x-amz-meta-')
            }
        else:
            out.meta = {}
        if 'local-creation-time' in out.meta:
            out.date = parse_date(out.meta['local-creation-time'],
                                  return_timestamp=False)
            del out.meta['local-creation-time']
        return out

    for obj in objects:
        o = format_object(obj)
        if o.name.endswith('/'): continue
        n = o.name[len(prefix) + 1 if prefix else 0:].split('/')
        if metainfo and n[-1].lower() in metainfo_files:
            foldername = '/'.join(n[:-1])
            apply_metainfo_file(obj, o.name, foldername,
                                metainfo_files[n[-1].lower()])
        if exclude:
            skip = False
            for x in exclude:
                if fnmatch.fnmatch(n[-1], x) or fnmatch.fnmatch(o.name, x):
                    skip = True
                    break
            if skip: continue
        if len(n) == 1:
            append_file(n[-1], o.size, o.date, meta=o.meta)
        else:
            # we have a file in a "folder"
            foldername = '/'.join(n[:-1])
            if not recursive and prefix != foldername:
                append_folder(n[0])
                append_file(n[-1],
                            o.size,
                            o.date,
                            '/'.join(n[:-1]),
                            meta=o.meta,
                            update_info_only=True)
                continue
            append_folder(foldername)
            append_file(n[-1], o.size, o.date, '/'.join(n[:-1]), meta=o.meta)

    return structure
