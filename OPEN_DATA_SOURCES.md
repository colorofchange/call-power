Open Data Sources
==============

CallPower relies on open government data to match callers with campaign targets.

We store a cached copy of this data with each deployment, to ensure lookups are fast and reliable.

Data is provided under the original license of the data provider. 

* US Congress contact data from [UnitedStates/congress](https://github.com/unitedstates/congress), public domain
* US Governors contact data scraped from [National Governors Association](https://github.com/spacedogXYZ/us_governors_contact), all rights reserved
* US States legislature contact data from [OpenStates API](http://docs.openstates.org/en/latest/api/)

* Canadan Member of Parliament contact data from [Represent](http://represent.opennorth.ca), licenses available from [OpenNorth](https://github.com/opennorth/represent-canada-data)

Update Instructions
-------------------

US Congress contact information and boundaries change regularly after elections. To update: 

    cd call_server/political_data/data
    make clean
    make
    cd ../../..
    python manager.py loadpoliticaldata

Geocoding
---------

To lookup address or zipcode to lat/lon, we use the [GeoPy library](https://geopy.readthedocs.io/en/1.11.0/#module-geopy.geocoders). The provider backend is configurable, but defaults to the [OSM Nominatim](https://nominatim.openstreetmap.org). Usage of this free resource must abide by [their policies](https://operations.osmfoundation.org/policies/nominatim/).

For faster responses and more reliable fuzzy-location matching, we suggest using [SmartyStreets](https://smartystreets.com) or [Google Maps Geocoding API](https://developers.google.com/maps/documentation/geocoding/start). To use these provides you will need to put the API key in the application environment as GEOCODE_API_KEY.