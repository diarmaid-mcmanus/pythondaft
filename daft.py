import requests
import json


class MapperInterface(object):
    """Scraper"""

    def scrape_listing_images(self, path):
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
            url = image.get('data-original')
            if url.startswith('//'):
                url = 'http:' + url
    
            images.append(url)
    
        return images

    
    def _generate_coordinates_for_url(self, sw, ne):
        """Take pair of lattitude and longitude and return a string."""
        # &sw=(51.93173528395185%2C+-10.03197265625)&ne=(55.031189853816535%2C+-5.59498046875)
        southwest = '&sw=(' + sw[0] + '%2C+' + sw[1] + ')'
        northeast = '&ne=(' + ne[0] + '%2C+' + ne[1] + ')'
        return southwest + northeast
    
    def _generate_url(self, action, property_type, sw, ne):
        """Return a valid daft.ie URL as a string."""
        base_url = 'http://www.daft.ie/ajax_endpoint.php?action='
        url_type = '&type=' + property_type
        url_coords = self._generate_coordinates_for_url(sw, ne)
        extra_params = '&extra_params=%7B%22rent%22%3A%5B0%2C50000000%5D%2C%22beds%22%3A%5B0%2C20%5D%7D'
        url = base_url + action + url_type + url_coords + extra_params
        return url
    
    def _divvy_up_ireland(self):
        """Return a list of coordinates covering Ireland."""
        # TODO replace coords.json file with config variable?
        with open('coordinates.json') as data_file:
            data = json.load(data_file)
        return data
        
    def _make_request(self, property_type, sw, ne):
        sw[0] += (".0000000")
        sw[1] += (".0000000")
        ne[0] += (".0000000")
        ne[1] += (".0000000")
        url = self._generate_url('map_nearby_properties', property_type, sw, ne)
        properties = requests.get(url)
        return properties.json()
    
    def get_all_properties_to_rent(self):
        """Return a collection of all properties for rent in Ireland."""
        sw = [ '51.93173528395185', '-10.03197265625' ]
        ne = [ '55.031189853816535', '-5.59498046875' ]
    
        all_rentals = self._make_request('rental', sw, ne)
        
        return all_rentals.json()
    
    def get_all_properties_for_sale(self):
        """Return a collection of all properties for sale in Ireland."""
        data = []
        for daft_coordinates in self._divvy_up_ireland():
            json = self._make_request('sale', daft_coordinates['sw'], daft_coordinates['ne'])
            data += json
        return data
    

if __name__=="__main__":
    scraper = MapperInterface()
    all_properties = scraper.get_all_properties_for_sale();
    output = open('outputfile', "w")
    output.write(str(all_properties))
