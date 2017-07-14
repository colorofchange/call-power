from collections import OrderedDict

# dict of {timespan_name : [python strftime(str), sqlalchemy to_char(str)]
API_TIMESPANS = OrderedDict([
    ('minute', ['%Y-%m-%d %H:%M', 'YYYY-MM-DD HH24:MI']),
    ('hour', ['%Y-%m-%d %H:00', 'YYYY-MM-DD HH24:00']),
    ('day', ['%Y-%m-%d', 'YYYY-MM-DD']),
    # ('week', '%Y W%U'), # format not supported by iso8601.js
    ('month', ['%Y-%m', 'YYYY-MM']),
    ('year', ['%Y', 'YYYY'])
])
