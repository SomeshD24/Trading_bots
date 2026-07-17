import datetime
import calendar
import requests
from logger import logger

# Holidays list (will be populated dynamically)
NSE_HOLIDAYS = []

def fetch_official_holidays():
    """
    Fetches the official holiday calendar from BSE/NSE.
    Since official exchanges often have complex scraping protections,
    in production this should hit a reliable data vendor API or a locally cached CSV.
    For this stub, we load a baseline set of known holidays.
    """
    global NSE_HOLIDAYS
    logger.info("Fetching official holiday calendar...")
    # Example REST call:
    # response = requests.get("https://api.example.com/nse_holidays")
    # NSE_HOLIDAYS = [datetime.datetime.strptime(d, "%Y-%m-%d").date() for d in response.json()['holidays']]
    
    # Fallback mock for paper trading
    NSE_HOLIDAYS = [
        datetime.date(2026, 1, 26), 
        datetime.date(2026, 8, 15),
        datetime.date(2026, 10, 2),
        datetime.date(2026, 12, 25),
    ]

# Initialize holidays
fetch_official_holidays()

def is_holiday_or_weekend(d):
    if d.weekday() >= 5: # Saturday or Sunday
        return True
    if d in NSE_HOLIDAYS:
        return True
    return False

def get_previous_business_day(d):
    d -= datetime.timedelta(days=1)
    while is_holiday_or_weekend(d):
        d -= datetime.timedelta(days=1)
    return d

def get_monthly_expiry(year, month):
    """
    Returns the last Tuesday of the given month. 
    If that day is a holiday, shifts to previous business day.
    """
    last_day = calendar.monthrange(year, month)[1]
    d = datetime.date(year, month, last_day)
    
    # Backtrack to the last Tuesday (Tuesday is 1 in weekday(), where Mon=0)
    while d.weekday() != 1:
        d -= datetime.timedelta(days=1)
        
    if is_holiday_or_weekend(d):
        d = get_previous_business_day(d)
        
    return d

def get_weekly_expiry(base_date=None):
    """
    Returns the weekly expiry for Nifty (Tuesday).
    Rule: From Monday onwards, buy the next weekly expiry (skip the immediate Tuesday if today is Mon/Tue).
    """
    if base_date is None:
        base_date = datetime.date.today()
    
    d = base_date
    
    # If today is Monday (0) or Tuesday (1), we want to skip the upcoming/current Tuesday
    # by jumping forward a week, ensuring we buy the *next* weekly expiry.
    if d.weekday() in (0, 1):
        d += datetime.timedelta(days=7)
        
    # Find the Tuesday (1) of the week 'd' is in
    while d.weekday() != 1:
        d += datetime.timedelta(days=1)
        
    if is_holiday_or_weekend(d):
        d = get_previous_business_day(d)
        
    return d

def get_current_and_next_monthly_expiries(current_date=None):
    if current_date is None:
        current_date = datetime.date.today()
        
    current_expiry = get_monthly_expiry(current_date.year, current_date.month)
    
    # If we have already passed this month's expiry, the "current" is next month's
    if current_date > current_expiry:
        # Move to next month
        next_month = current_date.month % 12 + 1
        next_year = current_date.year + (1 if current_date.month == 12 else 0)
        current_expiry = get_monthly_expiry(next_year, next_month)
        
    # Calculate next expiry
    next_month_for_next_expiry = current_expiry.month % 12 + 1
    next_year_for_next_expiry = current_expiry.year + (1 if current_expiry.month == 12 else 0)
    next_expiry = get_monthly_expiry(next_year_for_next_expiry, next_month_for_next_expiry)
    
    return current_expiry, next_expiry
