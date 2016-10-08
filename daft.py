import ConfigParser
import requests
import json
import lxml.html
from elasticsearch import Elasticsearch


class MapperInterface(object):
    """Scraper"""

    def __init__(self, coordinates_file='coordinates.json'):
        self.es = Elasticsearch()
        self.coordinates_file = coordinates_file

    def _get_listing_images(self, path):
        """Returns the images in a listing.

        stolen from https://github.com/Danm72/DaftPy"""
        r = requests.get("http://www.daft.ie%s" % (path,))
        if r.status_code is not 200:
            raise Exception("Failed to scrape image for %s" % (path,))
        tree = lxml.html.fromstring(r.text)
        results = tree.cssselect('#pbxl_carousel ul li.pbxl_carousel_item img')
        if len(results) < 1:
            raise NoImageFound(path)
        images = []
        for image in results:
            url = image.get('src')
            if url.startswith('//'):
                url = 'https:' + url
            images.append(url)
        return images

    def _generate_url(self, action, property_type, sw, ne):
        """Return a valid daft.ie URL as a string."""
        base_url = 'http://www.daft.ie/ajax_endpoint.php?action='
        extra_params = ('&extra_params={{"rent"%3A[0%2C50000000]'
                        '%2C"beds"%3A[0%2C20]}}')
        url = '{0}{1}&type={2}&sw=({3}%2C+{4})&ne=({5}%2C+{6}){7}'.format(
            base_url, action, property_type, sw[0], sw[1], ne[0], ne[1],
            extra_params)
        return url

    def _divvy_up_ireland(self):
        """Return a list of coordinates covering Ireland."""
        with open(self.coordinates_file) as data_file:
            data = json.load(data_file)
        return data

    def _make_request(self, property_type, sw, ne):
        sw[0] += (".03173528395185")
        sw[1] += (".03197265625")
        ne[0] += (".031189853816535")
        ne[1] += (".59498046875")
        url = self._generate_url('map_nearby_properties', property_type,
                                 sw, ne)
        properties = requests.get(url)
        return properties.json()

    def get_all_properties_to_rent(self):
        """Return a collection of all properties for rent in Ireland."""
        sw = ['51.93173528395185', '-10.03197265625']
        ne = ['55.031189853816535', '-5.59498046875']
        all_rentals = self._make_request('rental', sw, ne)
        return all_rentals.json()

    def get_all_properties_for_sale(self):
        """Return a collection of all properties for sale in Ireland."""
        data = []
        for coords in self._divvy_up_ireland():
            json = self._make_request('sale', coords['sw'], coords['ne'])
            for abode in json:
                try:
                    abode['images'] = self._get_listing_images(abode['link'])
                except NoImageFound:
                    abode['images'] = None
            data += json
        return data


class NoImageFound(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


if __name__ == "__main__":
    # load config with default defaults
    config = ConfigParser.SafeConfigParser(
                        {'coordinates_file': 'coordinates.json',
                         'eshost': 'localhost',
                         'esport': '9200'})
    config.readfp(open('daft.cfg'))
    coordinates_file = config.get('daftconfig', 'coordinates_file')
    eshost = config.get('daftconfig', 'eshost')
    esport = config.get('daftconfig', 'esport')

    scraper = MapperInterface(coordinates_file)
    abodes = scraper.get_all_properties_for_sale()
    es = Elasticsearch({'host': eshost, 'port': esport})
    for abode in abodes:
        es.index(index="daft-properties", doc_type='daft_listing', body=abode)
