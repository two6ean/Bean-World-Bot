from datetime import datetime, timezone, timedelta

def get_korean_time():
    KST = timezone(timedelta(hours=9))
    return datetime.now(KST)