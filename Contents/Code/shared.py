from time import strptime, sleep
from calendar import timegm
from json import loads

NAME       = 'Sonarr'
PLEX_PATH  = '/video/sonarr'

API_URL  = "{server}/api/{endpoint}"

ICONS = {
        "default":  "sonarr-content-icon.png",
        "series":   "icon-series.png",
        "calendar": "icon-calendar.png",
        "activity": "icon-activity.png",
        "wanted":   "icon-wanted.png",
        "settings": "icon-settings.png",
        "system":   "icon-system.png",
}

def ApiRequest(method, endpoint, params=None, cacheTime=0):

        url     = API_URL.format(server=Prefs['address'], endpoint=endpoint)
        headers = {"X-Api-Key": Prefs['apikey']}

        data = {}
        try:
                if method == 'post':
                        data = JSON.ObjectFromString(HTTP.Request(url=url, data=JSON.StringFromObject(params), headers=headers).content)
                elif method == 'get':
                        # dont use plex's JSON object from string because it has a fixed limit on the size of a string.
                        # some api calls (such as /episode) can exceed the limit.
                        data = loads(HTTP.Request(url=UrlEncode(url,params), headers=headers, cacheTime=cacheTime).content)
        except Exception, e:
                Log(e)

        return data  

def UrlEncode(url, params):

        return '%s?%s' % (url, '&'.join(["%s=%s" % (k,v) for k,v in params.iteritems()])) if params else url

def GetServer():

        return Prefs['address'] if not Prefs['address'].endswith("/") else Prefs['address'][:-1]

def ErrorMessage(error, message):

        return ObjectContainer(
                header  = u'%s' % error,
                message = u'%s' % message, 
        )                

# images comes as a list of objects. Turn it into a dict with key=image type, value=url. also prepend the server url if its a relative path.
def ProcessImages(images):

        return {
                img['coverType']: (img['url'] if not img['url'].startswith("/") else GetServer()+"/api"+img['url']) for img in images
        }

def QueueSize():

        return len(ApiRequest(method='get', endpoint='queue'))

def WantedMissingSize():

        params = {'page':1, 'pageSize':1, 'sortKey':'airDateUtc', 'sortDir':'desc'}
        try:
                x = int(ApiRequest(method='get', endpoint='wanted/missing', params=params)['totalRecords'])
                return x
        except:
                return 0
        
# make human readable sizes from bytes
def sizeof_fmt(num, suffix='B'):

        for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
                if abs(num) < 1024.0:
                        return "%3.1f%s%s" % (num, unit, suffix)
                num = num/1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)

# convert UTC timestamps to local time.
def utc_to_local(utc_dt):
        timestamp = timegm(utc_dt.timetuple())
        local_dt = Datetime.FromTimestamp(timestamp)
        assert utc_dt.resolution >= Datetime.Delta(microseconds=1)
        return local_dt.replace(microsecond=utc_dt.microsecond)

# plex clients support unicode. given an airtime, give an approximate unicode clock symbol
def AirTimeToUnicodeClocks(airtime):
        # clients that don't like these characters
        if Client.Platform in ['Plex Home Theater']: return "⚫"

        hour = airtime.hour-12 if airtime.hour > 11 else airtime.hour
        # there are only :00 and :30 clocks. use the nearest one.
        if airtime.minute in (x for y in (range(45,60), range(0,15)) for x in y):
                return {
                        0:"🕛", 1:"🕐", 2:"🕑", 3:"🕒", 4: "🕓", 5: "🕔",
                        6:"🕕", 7:"🕖", 8:"🕗", 9:"🕘", 10:"🕙", 11:"🕚",
                }[hour]
        else:
                return {
                        0:"🕧", 1:"🕜", 2:"🕝", 3:"🕞", 4: "🕟", 5: "🕠",
                        6:"🕡", 7:"🕢", 8:"🕣", 9:"🕤", 10:"🕥", 11:"🕦",
                }[hour]    

def IsInQueue(episodeId):

        data = ApiRequest(method='get', endpoint='queue', cacheTime=CACHE_1MINUTE)

        for item in data:
                if item['episode']['id'] == episodeId:
                        timeleft = strptime(item['timeleft'].split('.')[0], "%H:%M:%S") if 'timeleft' in item else time.localtime(0)
                        return (True, timeleft)

        return (False, None)

def StatusChecker(commandId, commandDescription=None, pollRate=0.5, maxPolls=30):

        # Check the status
        data = ApiRequest(method='get', endpoint='command/%d' % commandId, cacheTime=0)
        commandName = data['body']['name']
        messages = set()
        lastData = None
        for x in xrange(maxPolls):
                sleep(pollRate)
                data = ApiRequest(method='get', endpoint='command/%d' % commandId, cacheTime=0)

                if data == lastData:
                        continue
                        
                startTime = data['stateChangeTime'] if 'stateChangeTime' in data else data['startedOn']
                message = data['message'] if 'message' in data else "..."
                messages.add((startTime, message))

                if data['state'] == 'completed':
                        Dict['alerts'].append({'command': commandName, 'id': commandId, 'messages': messages})
                        Dict.Save()
                        return

                lastData = data