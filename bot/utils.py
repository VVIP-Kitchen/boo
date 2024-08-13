import datetime
import pytz


def get_time_based_greeting():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.datetime.now(ist)
    if 5 <= now.hour < 12:
        return "Good morning"
    elif 12 <= now.hour < 18:
        return "Good afternoon"
    elif 18 <= now.hour < 22:
        return "Good evening"
    else:
        return "Hello"
