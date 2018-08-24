# define flask extensions in separate file, to resolve import dependencies

from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

from flask_caching import Cache
cache = Cache()

from flask_assets import Environment
assets = Environment()

from flask_babel import Babel
babel = Babel()

from flask_mail import Mail
mail = Mail()

from flask_login import LoginManager
login_manager = LoginManager()

from flask_restless import APIManager
rest = APIManager()

from flask_wtf.csrf import CSRFProtect
csrf = CSRFProtect()

from flask_cors import CORS as cors

from flask_store import Store
store = Store()

from flask_rq2 import RQ
rq = RQ()

from flask_talisman import Talisman
CALLPOWER_CSP = {
    'default-src':'\'self\'',
    'script-src':['\'self\'', '\'unsafe-inline\'', '\'unsafe-eval\'', # for local scripts
        'cdnjs.cloudflare.com', 'ajax.cloudflare.com', 'media.twiliocdn.com',  # required for jquery, twilio
        'js-agent.newrelic.com', '*.nr-data.net'], # additional analytics platforms
    'style-src': ['\'self\'', '\'unsafe-inline\'', 'fonts.googleapis.com'], 
    'font-src': ['\'self\'', 'data:', 'fonts.gstatic.com'],
    'media-src': ['\'self\'', 'blob:', 'media.twiliocdn.com'],
    'connect-src': ['\'self\'', 'https://*.twilio.com', 'wss://*.twilio.com', 'media.twiliocdn.com', 'openstates.org'],
    'object-src': ['\'self\'', 'blob:'],
    'img-src': ['\'self\'', 'data:']
}
# unsafe-inline needed to render <script> tags without nonce
# unsafe-eval needed to run bootstrap templates
talisman = Talisman()

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
limiter = Limiter(key_func=get_remote_address)
