import datetime
import pytz
import dateutil.parser
import time

#from dates import *




def make_aware(date,zone='Europe/Berlin',force=False):
    """
        convert a date into a zone aware date

        Args:
            zone [string]: the string descriptor for the zone (https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568)
            force [bool]: if force is set, we se the zone of the date to zone
                            if force is false we don't set the zone of dates that have a zone already
        Returns:
            a date zone aware datetime objec
    """

    tz = pytz.timezone(zone)

    if date.tzinfo is not None and date.tzinfo.utcoffset(date) is not None:
        #is aware already,
        if force:
            date = date.astimezone(tz)
    else:
        tz.localize(date)
        date = date.astimezone(tz)
    return date


def date2secs(value,ignoreError = True,zone = 'Europe/Berlin'):
    """ converts a date with timezone into float seconds since epoch
    Args:
        value: the date given as either a string or a datetime object
        ignoreError: True: we return value if we can't convert
                     Fale: we return None if we can't convert
        zone: the zone used if the incoming has no zone
    Returns:
        the seconds since epoch or the original value of not convertibel
    """
    if type(value) == type(datetime.datetime(1970, 1, 1, 0, 0)):
        value = make_aware(value,zone=zone)
        timeDelta = value - datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.UTC)
        return timeDelta.total_seconds()
    elif type(value) == type(datetime.date(1970,1,1)):
        timeDelta = value - datetime.date(1970, 1, 1)
        return timeDelta.total_seconds()
    elif type(value) is str:
        #try a string parser
        try:
            date = dateutil.parser.parse(value)
            date=make_aware(date,zone=zone)
            timeDelta = date - datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.UTC)
            return timeDelta.total_seconds()
        except:
            if ignoreError:
                return value
            else:
                return None
    else:
        if ignoreError:
            return value
        else:
            return None



def date2msecs(value):
    """
        converst a timestamp in to ms since epoch
    """
    return date2secs(value)*1000

def secs2date(epoch):
    """ converts float seconds since epoch into datetime object with UTC timezone """
    return datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.UTC) + datetime.timedelta(seconds=epoch)

def secs2dateString(epoch,tz="+00:00"):
    """ converts seconds since epoch into a datetime iso string format 2009-06-30T18:30:00.123456+02:00 """
    try:
        stri = secs2date(epoch).isoformat()
        return stri
    except:
        return None

def epochToIsoString(epoch,zone=pytz.UTC):
    if type(zone) is str:
        zone = pytz.timezone(zone)
    dat = datetime.datetime(1970, 1, 1, 0, 0,tzinfo=pytz.utc) + datetime.timedelta(seconds=epoch)
    dat=dat.astimezone(zone) # we must do this later conversion due to a bug in tz lib
    return dat.isoformat()

def now_iso(zone='Europe/Berlin'):
    return epochToIsoString(time.time(), zone=zone)