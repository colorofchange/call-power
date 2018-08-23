import countries
import importlib

COUNTRY_CHOICES = [
    ('us', "United States"),
    ('ca', "Canada"),
    ('fr', "France"),
    ('de', "Germany"),
    ('es', "Spain"),
    ('ir', "Ireland"),
    ('it', "Italy"),
    ('pl', "Poland"),
    ('uk', "United Kingdom"),
]

COUNTRY_DATA = {
    'us': 'call_server.political_data.countries.us.USDataProvider',
    'ca': 'call_server.political_data.countries.ca.CADataProvider',
    'fr': 'call_server.political_data.countries.eu.FRDataProvider',
    'de': 'call_server.political_data.countries.eu.DEDataProvider',
    'es': 'call_server.political_data.countries.eu.ESDataProvider',
    'ir': 'call_server.political_data.countries.eu.IRDataProvider',
    'it': 'call_server.political_data.countries.eu.ITDataProvider',
    'pl': 'call_server.political_data.countries.eu.PLDataProvider',
    'uk': 'call_server.political_data.countries.eu.UKDataProvider',
}

class NoDataProviderError(Exception):
    def __init__(self, country_code):
        self.message = "No data provider available for country code '{}'".format(country_code)


def load_data(cache):
    n = 0
    for country_code in COUNTRY_DATA.keys():
        country_data = get_country_data(country_code, cache=cache)
        n += country_data.load_data()
    return n

def get_country_data(country_code, **kwargs):
    data_provider_class = _get_data_provider_class(country_code)
    return data_provider_class(**kwargs)

def _get_data_provider_class(country_code):
    country_code = country_code.lower()

    path = COUNTRY_DATA.get(country_code)

    if path is None:
        raise NoDataProviderError(country_code)

    try:
        module_name, class_name = path.rsplit('.', 1)
    except ValueError:
        raise NoDataProviderError(country_code)

    try:
        module = importlib.import_module(module_name)
        data_provider_class = getattr(module, class_name)
        return data_provider_class
    except (ImportError, AttributeError) as e:
        raise NoDataProviderError(country_code)

# import this at the end, because it depends on get_country_data above
from .views import political_data
from .data_cache import check_political_data_cache
