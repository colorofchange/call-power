SEGMENT_BY_LOCATION = 'location'
SEGMENT_BY_CUSTOM = 'custom'
SEGMENT_BY_CHOICES = (
    (SEGMENT_BY_LOCATION, 'Location'),
    (SEGMENT_BY_CUSTOM, 'Custom')
)

LOCATION_POSTAL = 'postal'
LOCATION_ADDRESS = 'address'
LOCATION_LATLON = 'latlon'
LOCATION_DISTRICT = 'district'
LOCATION_CHOICES = (
    ('', 'None'),
    (LOCATION_POSTAL, 'ZIP / Postal Code'),
    (LOCATION_ADDRESS, 'Street Address'),
    (LOCATION_LATLON, 'Lat / Lon'),
    (LOCATION_DISTRICT, 'District')
)

INCLUDE_SPECIAL_FIRST = 'first'
INCLUDE_SPECIAL_LAST = 'last'
INCLUDE_SPECIAL_ONLY = 'only'
INCLUDE_SPECIAL_CHOCIES = (
    ('', '- choose order -'),
    (INCLUDE_SPECIAL_FIRST, 'Before'),
    (INCLUDE_SPECIAL_LAST, 'After'),
    (INCLUDE_SPECIAL_ONLY, 'Only If'),
)

TARGET_OFFICE_DISTRICT = 'district'
TARGET_OFFICE_BUSY = 'busy'
# TARGET_OFFICE_CLOSEST = 'closest'
TARGET_OFFICE_CHOICES = (
    ('', 'Default'),
    (TARGET_OFFICE_DISTRICT, 'District'),
    # (TARGET_OFFICE_BUSY, 'Main Busy'),
    # (TARGET_OFFICE_CLOSEST, 'Closest'),
)

STATUS_ARCHIVED = 0
STATUS_PAUSED = 1
STATUS_LIVE = 2
CAMPAIGN_STATUS = {
    STATUS_ARCHIVED: 'archived',
    STATUS_PAUSED: 'paused',
    STATUS_LIVE: 'live',
}

EMBED_FORM_CHOICES = (
    ('', 'None'),
    ('iframe', 'iFrame'),
    ('custom', 'Javascript'),
)

EMBED_SCRIPT_DISPLAY = (
    ('', 'None'),
    ('overlay', 'Overlay'),
    ('alert', 'Alert'),
    ('replace', 'Replace Form'),
    ('redirect', 'Redirect URL'),
    ('custom', 'Custom')
)


# empty set of choices, for filling in on client-side
EMPTY_CHOICES = {'': ''}

STRING_LEN = 100
TWILIO_SID_LENGTH = 34

# from https://www.twilio.com/docs/api/twiml/say#attributes-alice
# enable more when we get political data for other countries
LANGUAGE_CHOICES = (
    # ('da', 'Danish'),
    # ('de', 'German'),
    ('en', 'English'),
    # ('ca', 'Catalan'),
    ('es', 'Spanish'),
    # ('fi', 'Finnish'),
    ('fr', 'French'),
    # ('it', 'Italian'),
    # ('ja', 'Japanese'),
    # ('ko', 'Korean'),
    # ('no', 'Norwegian'),
    # ('nl', 'Dutch'),
    # ('pl', 'Polish'),
    # ('pt', 'Portuguese'),
    # ('ru', 'Russian'),
    # ('sv', 'Swedish'),
    # ('zh', 'Chinese'),
)