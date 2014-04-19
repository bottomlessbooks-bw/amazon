import base64
import functools
import hashlib
import hmac
import time
import urllib2

def import_name():
    return 'amazon'

def format_timestamp(ts=None): # don't make this time.gmtime(), it'll be snapped-to at import time
    if ts is None:
        ts = time.gmtime()
    return urllib2.quote(time.strftime("%Y-%m-%dT%H:%M:%SZ", ts))

def get_url_with_key(key, args):
    # make signature
    msg = 'GET\nwebservices.amazon.com\n/onca/xml\n' + '&'.join(sorted(args))
    unescaped_signature = base64.b64encode(hmac.new(key, msg, hashlib.sha256).digest())
    signature = urllib2.quote(unescaped_signature)

    # append signature and compose the url
    args.append('Signature={}'.format(signature))
    return 'http://webservices.amazon.com/onca/xml?{}'.format('&'.join(args))

def generate_func_get_url(key, static_args):
    local_key = key
    local_static_args = static_args[:]
    def inner_func(additional_args, ts=None):
        cur_args = local_static_args[:] # static args
        cur_args.append('Timestamp={}'.format(format_timestamp(ts))) # dynamic arcs
        cur_args.extend(additional_args) # additional args (from this call)
        return get_url_with_key(key, cur_args)
    return inner_func

def generate_func_item_search(key):
    static_args = [ 'Condition=Used',
                    'Service=AWSECommerceService',
                    'Operation=ItemSearch',
                    'AssociateTag=bottomlessboo-20',
                    'SearchIndex=Books',
                    'Availability=Available',
                    'AWSAccessKeyId=AKIAJOH5BFK3U2WGKXUQ',
                    'ResponseGroup=Offers', ]
    return generate_func_get_url(key, static_args)

def generate_func_item_lookup(key):
    static_args = [ 'Condition=Used',
                    'Service=AWSECommerceService',
                    'Operation=ItemLookup',
                    'AssociateTag=bottomlessboo-20',
                    'AWSAccessKeyId=AKIAJOH5BFK3U2WGKXUQ',
                    'ResponseGroup=Offers', ]
    return generate_func_get_url(key, static_args)
