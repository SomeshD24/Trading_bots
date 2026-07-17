import json
import os
from dotenv import load_dotenv
load_dotenv()

from feed import ChoiceAPIFeed
from symbol_master import SymbolMaster

master = SymbolMaster()
feed = ChoiceAPIFeed(master)
session_id = feed.login_with_otp(
    os.getenv('CHOICE_VENDOR_ID'),
    os.getenv('CHOICE_VENDOR_KEY'),
    os.getenv('CHOICE_API_KEY'),
    os.getenv('CHOICE_MOBILE_NO'),
    os.getenv('CHOICE_AES_KEY'),
    os.getenv('CHOICE_AES_IV')
)

print('Session ID:', session_id)
# Let's see if we can get positions
if hasattr(feed, 'api'):
    positions = feed.api.positionBook()
    print('Positions:', positions)
