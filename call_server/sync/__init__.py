from .views import sync
from .models import SyncCampaign, SyncCall
from .jobs import sync_campaigns

class SyncError(Exception):
    def __init__(self, message):
        self.message = message

