#-*- encoding: utf-8 -*-
# Sonarr for Plex Media Server
# v0.1 by Cory <babylonstudio@gmail.com>
# https://github.com/coryo/Sonarr.bundle
# https://github.com/Sonarr/Sonarr/wiki/API

import urllib, urllib2, time, calendar
from updater import Updater

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
                        # plex's JSON.ObjectFromURL will only urlencode a python dict as the post body. sonarr wants JSON encoded body.
                        req  = urllib2.Request(url=url, data=JSON.StringFromObject(params), headers=headers)
                        data = JSON.ObjectFromString(urllib2.urlopen(req).read())
                elif method == 'get':
                        # parameters url encoded. ex: api/Episode?seasonId={id}
                        url  = "%s?%s" % (url,urllib.urlencode(params)) if params else url
                        data = JSON.ObjectFromURL(url, headers=headers, cacheTime=cacheTime)
        except: pass

        return data

# A route to nowhere
@route(PLEX_PATH + '/void')
def Void():

        return ObjectContainer()

def GetServer():

        return Prefs['address'] if not Prefs['address'].endswith("/") else Prefs['address'][:-1]

def ErrorMessage(error, message):

        return ObjectContainer(
                header  = u'%s' % error,
                message = u'%s' % message, 
        )                

# for retrieving images from the server with the apikey header
@route(PLEX_PATH + '/getimage')
def GetImage(url):

        try:
                data = HTTP.Request(url=url, headers={"X-Api-Key": Prefs['apikey']} if Prefs['address'] in url else {}, cacheTime=CACHE_1WEEK).content
                return DataObject(data, 'image/jpeg')
        except:
                return Redirect(R(ICONS['default']))     

# images comes as a list of objects. Turn it into a dict with key=image type, value=url. also prepend the server url if its a relative path.
def ProcessImages(images):

        return {
                imageType['coverType']: (imageType['url'] if not imageType['url'].startswith("/") else GetServer()+"/api"+imageType['url']) for imageType in images
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

# convert UTC timestamps to local time. requires import calendar
def utc_to_local(utc_dt):
        timestamp = calendar.timegm(utc_dt.timetuple())
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
                        0:"🕛",
                        1:"🕐",
                        2:"🕑",
                        3:"🕒",
                        4:"🕓",
                        5:"🕔",
                        6:"🕕",
                        7:"🕖",
                        8:"🕗",
                        9:"🕘",
                        10:"🕙",
                        11:"🕚",
                }[hour]
        else:
                return {
                        0:"🕧",
                        1:"🕜",
                        2:"🕝",
                        3:"🕞",
                        4:"🕟",
                        5:"🕠",
                        6:"🕡",
                        7:"🕢",
                        8:"🕣",
                        9:"🕤",
                        10:"🕥",
                        11:"🕦",
                }[hour]    

def IsInQueue(episodeId):

        data = ApiRequest(method='get', endpoint='queue', cacheTime=2)

        for item in data:
                if item['episode']['id'] == episodeId:
                        timeleft = time.strptime(item['timeleft'], "%H:%M:%S.%f") if 'timeleft' in item else time.localtime(0)
                        return (True, timeleft)

        return (False, None)

####################################################################################################
# Main
####################################################################################################                 
def Start():

        ObjectContainer.title1 = NAME
        HTTP.CacheTime  = 0
        HTTP.User_Agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36'

        Dict['alerts'] = []

@handler(PLEX_PATH, NAME, thumb=ICONS['default'])
def MainMenu():       

        oc = ObjectContainer(no_cache=True)

        Updater(PLEX_PATH+'/updater', oc)
        DisplayAlerts(oc)

        if Prefs['address'] and Prefs['apikey']:
                oc.add(DirectoryObject(
                        key   = Callback(Series),
                        title = L('series'),
                        thumb = R(ICONS['series'])
                ))

                oc.add(DirectoryObject(
                        key   = Callback(Calendar),
                        title = L('calendar'),
                        thumb = R(ICONS['calendar'])
                ))

                oc.add(DirectoryObject(
                        key   = Callback(Queue),
                        title = u'%s (%d)' % (L('queue'), QueueSize()),
                        thumb = R(ICONS['activity'])
                ))

                oc.add(DirectoryObject(
                        key   = Callback(History),
                        title = L('history'),
                        thumb = R(ICONS['activity'])
                ))

                oc.add(DirectoryObject(
                        key   = Callback(WantedMissing, page=1, pageSize=20),
                        title = u'%s (%d)' % (L('wanted'), WantedMissingSize()),
                        thumb = R(ICONS['wanted'])
                ))
        else:
                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = "Please add a server in the channel preferences.",
                        thumb = R(ICONS['wanted'])
                ))

        oc.add(PrefsObject(
                title   = L('preferences'),
                tagline = L('preferences'),
                summary = L('preferences'),
                thumb   = R(ICONS['settings'])
        ))

        return oc

####################################################################################################

# Lists Episodes without files
@route(PLEX_PATH + '/wantedmissing/{pageSize}/{page}', page=int, pageSize=int)
def WantedMissing(page=1, pageSize=20):

        oc = ObjectContainer(title2=L('wanted'))
        DisplayAlerts(oc)

        params = {'page':     page,
                  'pageSize': pageSize,
                  'sortKey': 'airDateUtc',
                  'sortDir': 'desc'}

        data = ApiRequest(method='get', endpoint='wanted/missing', params=params)

        if data:
                for item in data['records']:
                        AppendEpisodeToContainer(item, oc, titleFormat='status,date,time,show,epnum,title')

        if len(oc) >= pageSize:
                oc.add(NextPageObject(
                        key = Callback(WantedMissing, page=page+1, pageSize=pageSize)
                ))

        return oc

# Returns all series in your collection
@route(PLEX_PATH + '/series')
def Series():

        oc = ObjectContainer(title2=L('series'), no_cache=True)
        DisplayAlerts(oc)

        data = ApiRequest(method='get', endpoint='series')

        for item in data:
                title  = item['title']
                images = ProcessImages(item['images'])

                oc.add(DirectoryObject(
                        key   = Callback(Seasons, title=title, seriesId=item['id']),
                        title = title,
                        thumb = Callback(GetImage, url=images['poster'])
                ))

        return oc

# This may timeout on very large shows
@route(PLEX_PATH + '/seasons/{seriesId}', seriesId=int)
def Seasons(title, seriesId):

        oc = ObjectContainer(title2=title)
        DisplayAlerts(oc)

        data = ApiRequest(method='get', endpoint='episode', params={"seriesId": seriesId}, cacheTime=10)

        seasons = set(episode['seasonNumber'] for episode in data)

        for season in list(reversed(list(seasons))):
                oc.add(DirectoryObject(
                        key   = Callback(Season, seriesId=seriesId, seasonNumber=season),
                        title = "%s %d" % (L("season"), season),
                        thumb = R(ICONS['default'])
                ))

        return oc

@route(PLEX_PATH + '/season/{seriesId}/{seasonNumber}', seasonNumber=int)
def Season(seriesId, seasonNumber):

        oc = ObjectContainer(title2='%s %d'%(L('season'), seasonNumber))
        DisplayAlerts(oc)

        data = ApiRequest(method='get', endpoint='episode', params={"seriesId": seriesId}, cacheTime=10)

        for episode in list(reversed(data)):
                if episode['seasonNumber'] != seasonNumber:
                        continue

                AppendEpisodeToContainer(episode, oc, titleFormat='status,epnum,title')

        return oc

# Sonarr searches its indexers and lists the available releases for episodeId. TODO: Make this do something
@route(PLEX_PATH + '/release/{episodeId}', episodeId=int)
def Release(episodeId):

        oc = ObjectContainer()
        DisplayAlerts(oc)

        data = ApiRequest(method='get', endpoint="release", params={"episodeId": episodeId})

        for item in data:
                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = '%s - %s' % (item['indexer'], item['title']),
                        thumb = R(ICONS['series'])
                ))

        return oc

@route(PLEX_PATH + '/calendar')
def Calendar(startDate=None, endDate=None):

        oc = ObjectContainer(title2=L("calendar"), no_cache=True)
        DisplayAlerts(oc)

        start_offset = int(Prefs['calendarstartday'])
        total_days   = int(Prefs['calendardays'])

        if not startDate or not endDate:
                now       = Datetime.Now()
                startDate = (now - Datetime.Delta(days=start_offset)).strftime("%Y-%m-%d")
                endDate   = (now + Datetime.Delta(days=total_days-start_offset)).strftime("%Y-%m-%d")

        start_dt = Datetime.ParseDate(startDate)
        end_dt   = Datetime.ParseDate(endDate)

        if Prefs['calendarnav']:
                oc.add(DirectoryObject(
                        key = Callback(Calendar, startDate = (start_dt - Datetime.Delta(days=total_days)).strftime("%Y-%m-%d"),
                                                 endDate   = (end_dt   - Datetime.Delta(days=total_days)).strftime("%Y-%m-%d")),
                        title = "<< Back %d Day(s)" % total_days,
                        thumb = R(ICONS['calendar'])
                ))
                oc.add(DirectoryObject(
                        key = Callback(Calendar, startDate = (start_dt + Datetime.Delta(days=total_days)).strftime("%Y-%m-%d"),
                                                 endDate   = (end_dt   + Datetime.Delta(days=total_days)).strftime("%Y-%m-%d")),
                        title = "Next %d Day(s) >>" % total_days,
                        thumb = R(ICONS['calendar'])
                ))

        data = ApiRequest(method='get', endpoint='calendar', params={"start":startDate, "end":endDate})

        lastDay = None
        for item in data:
                if Prefs['calendardividers']:
                        date = utc_to_local(Datetime.ParseDate(item['airDateUtc'])) if Prefs['uselocaltime'] else Datetime.ParseDate(item['airDateUtc'])
                        if date.day != lastDay:
                                oc.add(DirectoryObject(
                                        key   = Callback(Void),
                                        title = u'--[ %s ]------------------------------------------------------------------------' % date.strftime('%a, %b %d'),
                                        thumb = R(ICONS['calendar'])
                                ))
                        lastDay = date.day
                        AppendEpisodeToContainer(item, oc, titleFormat='status,time,show,epnum,title')
                else:
                        AppendEpisodeToContainer(item, oc, titleFormat='status,date,time,show,epnum,title')

        return oc

def AppendEpisodeToContainer(calendarItem, oc, titleFormat='status,date,time,show,epnum,title'):

        episodeId     = calendarItem['id']
        episodeFileId = calendarItem['episodeFileId']
        seriesType    = calendarItem['series']['seriesType']
        images        = ProcessImages(calendarItem['series']['images'])
        dateUtc       = Datetime.ParseDate(calendarItem['airDateUtc'])
        hasFile       = calendarItem['hasFile']  if 'hasFile'  in calendarItem else False
        summary       = calendarItem['overview'] if 'overview' in calendarItem else "N/A"

        isDownloading = False
        date = utc_to_local(dateUtc) if Prefs['uselocaltime'] else dateUtc

        if hasFile:
                status = u"✓"
        else:
                aired = utc_to_local(dateUtc) + Datetime.Delta(minutes=calendarItem['series']['runtime']) < Datetime.Now()
                if aired:
                        isDownloading,timeLeft = IsInQueue(episodeId)
                        status = u"▼ %dm %ds"%(timeLeft.tm_min, timeLeft.tm_sec) if (isDownloading and timeLeft) else u"✖"
                else:   
                        status = AirTimeToUnicodeClocks(date)

        titleElements = {
                'date':   date.strftime("%a"),
                'time':   date.strftime('%H:%M'),
                'status': status,
                'epnum':  'S{:02d}E{:02d}'.format(calendarItem['seasonNumber'], calendarItem['episodeNumber']) if seriesType == 'standard' else "",
                'show':   calendarItem['series']['title'],
                'title':  calendarItem['title'],
        }
        title = ' - '.join([titleElements[x] for x in titleFormat.split(',') if titleElements[x]])

        do = DirectoryObject()

        if hasFile:
                do.key = Callback(EpisodeFile, episodeFileId=episodeFileId)
        elif isDownloading:
                do.key = Callback(Void)
        else:
                do.key = Callback(EpisodeSearch, episodes=episodeId)

        do.title   = u'%s' % title
        do.summary = u'%s' % summary
        do.thumb   = Callback(GetImage, url=images['poster'])
        do.art     = Callback(GetImage, url=images['fanart'])

        oc.add(do)

# Sonarr does an automatic search for the given episodes. episodes is CSV episodeIds
@route(PLEX_PATH + '/EpisodeSearch/{episodes}')
def EpisodeSearch(episodes):

        oc = ObjectContainer()

        # Send the command
        params = {"name": "EpisodeSearch",
                  "episodeIds": episodes.split(',')}
        data   = ApiRequest(method='post', endpoint='command', params=params)

        if not data:
                return oc

        Thread.Create(StatusChecker, commandId=data['id'])

        return oc

def StatusChecker(commandId, commandDescription=None, pollRate=0.5):

        # Check the status
        data = ApiRequest(method='get', endpoint='command/%d' % commandId)
        commandName = data['body']['name']
        messages = set()
        lastData = None
        while data:
                time.sleep(pollRate)
                data = ApiRequest(method='get', endpoint='command/%d' % commandId)

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

def DisplayAlerts(oc):
          
        for x,alert in enumerate(Dict['alerts']):
                oc.add(DirectoryObject(
                        key   = Callback(CommandLog, x=x),
                        title = "%s #%s" % (alert['command'], alert['id']),
                        thumb = R(ICONS['wanted'])
                )) 

@route(PLEX_PATH + '/commandlog', x=int)
def CommandLog(x):

        oc = ObjectContainer()

        alert = Dict['alerts'][x]
        for time,message in alert['messages']:
                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = '%s - %s' % (time,message),
                ))
        del Dict['alerts'][x]

        return oc


# sortKey = "series.title" or "date"
@route(PLEX_PATH + '/history', page=int, pageSize=int)
def History(page=1, pageSize=20, sortKey="date", sortDir="desc"):

        oc = ObjectContainer(title2=L('history'), no_cache=True)
        DisplayAlerts(oc)

        data = ApiRequest(method='get', endpoint='history', params={"page":page, "pageSize":pageSize, "sortKey":sortKey, "sortDir":sortDir})

        if data:
                for item in data['records']:
                        dateUtc = Datetime.ParseDate(item['date'])
                        date = utc_to_local(dateUtc) if Prefs['uselocaltime'] else dateUtc
                        oc.add(DirectoryObject(
                                key = Callback(Void),
                                title = u'%s - [%s] - %s' % (date.strftime("%b %d, %H:%M"), item['eventType'], item['sourceTitle']),
                        ))

        if len(oc) >= pageSize:
                oc.add(NextPageObject(
                        key = Callback(History, page=page+1, pageSize=pageSize, sortKey=sortKey, sortDir=sortDir)
                ))

        return oc

@route(PLEX_PATH + '/queue')
def Queue():

        oc = ObjectContainer(title2=L('queue'), no_cache=True)
        DisplayAlerts(oc)

        data = ApiRequest(method='get', endpoint='queue')

        for item in data:
                images    = ProcessImages(item['series']['images'])
                protocol  = item['protocol']
                status    = item['status']
                itemtitle = item['title']
                timeleft  = item['timeleft'].split('.')[0] if 'timeleft' in item else "N/A"

                total_size = float(item['size'])
                remaining  = float(item['sizeleft'])
                completed  = total_size - remaining

                title = "{p} - {s} - {t}".format(p=protocol, s=status, t=itemtitle)
                summary = "Remaining: {time} - {x}/{y} - R={r}".format(time=timeleft, x=sizeof_fmt(completed), y=sizeof_fmt(total_size), r=sizeof_fmt(remaining))
                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = title,
                        thumb = Callback(GetImage, url=images['poster']),
                        summary = summary
                ))

        return oc

@route(PLEX_PATH + '/episodefile/{episodeFileId}', episodeFileId=int)
def EpisodeFile(episodeFileId):

        oc = ObjectContainer(title2='EpisodeFile %d' % episodeFileId)

        data = ApiRequest(method='get', endpoint='EpisodeFile/%d' % episodeFileId)

        if data:
                try:
                        dateUtc = Datetime.ParseDate(data['dateAdded'])
                        date = utc_to_local(dateUtc) if Prefs['uselocaltime'] else dateUtc
                        info = {
                                "Path": '/'.join(data['path'].split('/')[:-1]),
                                "File": data['path'].split('/')[-1],
                                "Size": sizeof_fmt(data['size']),
                                "Date Added": date.strftime("%Y/%m/%d, %H:%M:%S"),
                                "Quality": data['quality']['quality']['name'],
                        }
                        for k,v in info.iteritems():
                                oc.add(DirectoryObject(
                                        key = Callback(Void),
                                        title = "%s: %s" %(k,v)
                                ))
                except: pass
        
        return oc