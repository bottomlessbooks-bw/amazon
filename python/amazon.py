import base64
import functools
import hashlib
import hmac
import time
import urllib2
import xml.etree.ElementTree as ET

def import_name():
    return 'amazon'

# 
# URL-composing functions use these as helper functions
# 

def format_timestamp(ts=None): # don't make this time.gmtime(), it'll be snapped-to at import time
    if ts is None:
        ts = time.gmtime()
    return urllib2.quote(time.strftime("%Y-%m-%dT%H:%M:%SZ", ts))

# 
# these functions just compose the url, they don't fetch anything
# 

def get_url_with_key(key, args):
    # make signature
    msg = 'GET\nwebservices.amazon.com\n/onca/xml\n' + '&'.join(sorted(args))
    unescaped_signature = base64.b64encode(hmac.new(key, msg, hashlib.sha256).digest())
    signature = urllib2.quote(unescaped_signature)

    # append signature and compose the url
    args.append('Signature={}'.format(signature))
    return 'http://webservices.amazon.com/onca/xml?{}'.format('&'.join(args))

def generate_func_get_url(key, static_args, additional_args_processor):
    local_key = key
    local_static_args = static_args[:]
    def inner_func(additional_args, ts=None):
        cur_args = local_static_args[:] # static args
        cur_args.append('Timestamp={}'.format(format_timestamp(ts))) # dynamic arcs
        cur_args.extend(additional_args_processor(additional_args)) # additional args (from this call)
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
    def additional_args_processor(additional_args): # expects an iterable of keywords
        return [ 'Keywords={}'.format(urllib2.quote(' '.join(additional_args))), ]
    return generate_func_get_url(key, static_args, additional_args_processor)

def generate_func_item_lookup(key):
    static_args = [ 'Condition=Used',
                    'Service=AWSECommerceService',
                    'Operation=ItemLookup',
                    'AssociateTag=bottomlessboo-20',
                    'AWSAccessKeyId=AKIAJOH5BFK3U2WGKXUQ',
                    'ResponseGroup=Images%2COffers', ]
    def additional_args_processor(additional_args): # expects a single string which is the ASIN
        return [ 'ItemId={}'.format(additional_args), ]
    return generate_func_get_url(key, static_args, additional_args_processor)

def generate_func_item_batch_lookup(key):
    static_args = [ 'Condition=Used',
                    'Service=AWSECommerceService',
                    'Operation=ItemLookup',
                    'AssociateTag=bottomlessboo-20',
                    'AWSAccessKeyId=AKIAJOH5BFK3U2WGKXUQ',
                    'ResponseGroup=Images%2COffers',
                    'ItemLookup.Shared.IdType=ASIN', ]
    def additional_args_processor(additional_args): # expects a list of at most 2 ASINs
        return [ 'ItemLookup.{}.ItemId={}'.format(num+1, xx) for num, xx in enumerate(additional_args) ]
    return generate_func_get_url(key, static_args, additional_args_processor)

# 
# Helper functions to parse the data and build batched queries.
# 

def create_batch_urls(item_lookup_func, asins):
    return [ item_lookup_func(asins[ii:ii+2]) for ii in xrange(0, len(asins), 2) ]

def _extract_xmlns(root):
    # extract the xmlns (this is kind of rubbish)
    return root.tag.split('}', 1)[0] + '}' # does not fail gracefully!

def _generate_prefix_func(root):
    xmlns = _extract_xmlns(root)
    return lambda tags: '/'.join([ '{}{}'.format(xmlns, tt) for tt in tags ])

def _isvalid(root, prefix_func):
    isvalid = root.find(prefix_func([ 'Items', 'Request', 'IsValid', ]))
    return isvalid is not None and isvalid.text == 'True' # compare against the string 'True'

def extract_data_from_lookup(data):
    root = ET.fromstring(data)
    prefix = _generate_prefix_func(root)

    if not _isvalid(root, prefix):
        return []

    def extract_image_data(image_root, prefix_func):
        image_data = { 'url' : image_root.find(prefix_func([ 'URL', ])),
                       'height' : image_root.find(prefix_func([ 'Height', ])),
                       'width' : image_root.find(prefix_func([ 'Width', ])), }
        if image_data['url'] is not None: image_data['url'] = image_data['url'].text
        if image_data['height'] is not None: image_data['height'] = image_data['height'].text
        if image_data['width'] is not None: image_data['width'] = image_data['width'].text
        return image_data

    data = []
    for item in root.findall(prefix([ 'Items', 'Item', ])):
        item_data = {}
        item_data['small_image'] = extract_image_data(item.find(prefix([ 'MediumImage', ])), prefix)
        item_data['large_image'] = extract_image_data(item.find(prefix([ 'LargeImage', ])), prefix)

        asin = item.find(prefix([ 'ASIN', ]))
        item_data['asin'] = asin is not None and asin.text or None

        # TODO is the lowest used price always available? Maybe not.
        price = item.find(prefix( [ 'OfferSummary', 'LowestUsedPrice', 'FormattedPrice', ] ))
        item_data['lowest_used_price'] = price is not None and float(price.text.replace('$','')) or None

        availability = item.find(prefix( [ 'Offers', 'Offer', 'OfferListing', 'AvailabilityAttributes', 'AvailabilityType', ] ))
        item_data['availability'] = availability is not None and availability.text or None
        data.append(item_data)

    return data

def extract_asins_from_search(data, price_threshold=1.00):
    root = ET.fromstring(data)
    prefix = _generate_prefix_func(root)

    if not _isvalid(root, prefix):
        return []

    asins = []
    for item in root.findall(prefix([ 'Items', 'Item', ])):
        asin = item.find(prefix([ 'ASIN', ]))
        price = item.find(prefix( [ 'OfferSummary', 'LowestUsedPrice', 'FormattedPrice', ] ))
        if asin is not None and price is not None:
            price = float(price.text.replace('$',''))
            if price <= price_threshold:
                asins.append(asin.text)
    return asins
