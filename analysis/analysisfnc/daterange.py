from datetime import datetime, timedelta


def daterange(start_date_str, end_date_str, date_format="%Y-%m-%d"):
    """Generate dates between start_date_str and end_date_str inclusive in string format."""
    start_date = datetime.strptime(start_date_str, date_format)
    end_date = datetime.strptime(end_date_str, date_format)
    for n in range(int((end_date - start_date).days) + 1):
        yield (start_date + timedelta(n)).strftime(date_format)
