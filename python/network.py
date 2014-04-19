import gzip
import functools
import StringIO
import urllib2

def import_name():
    return 'network'

def fetch_url(opener, url):
    response = opener.open(url)
    data = response
    if response.info().get('Content-Encoding') == 'gzip':
        data = gzip.GzipFile(fileobj=StringIO.StringIO(response.read()))

    return data.read()

def generate_func_fetch_url():
    opener = urllib2.build_opener()
    opener.addheaders = [ ('User-agent', 'python/BottomlessBooks'),
                          ('Connection', 'close'),
                          ('Accept-Encoding', 'gzip,identity'), ]
    return functools.partial(fetch_url, opener)
