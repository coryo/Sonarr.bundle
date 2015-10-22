# Sonarr for Plex Media Server
# v0.1 by Cory <babylonstudio@gmail.com>
# https://github.com/Sonarr/Sonarr/wiki/API

import urllib, urllib2, time
from updater import Updater

NAME       = 'Sonarr'
PLEX_PATH  = '/applications/sonarr'

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
                elif method == 'get2':
                        # parameter in the url. ex api/Episode/{id}
                        url  = "%s/%s" % (url,params) if params else url
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
        

def sizeof_fmt(num, suffix='B'):
        for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
                if abs(num) < 1024.0:
                        return "%3.1f%s%s" % (num, unit, suffix)
                num = num/1024.0
        return "%.1f%s%s" % (num, 'Yi', suffix)        

####################################################################################################
# Main
####################################################################################################                 
def Start():

        ObjectContainer.title1 = NAME
        HTTP.CacheTime  = 0
        HTTP.User_Agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36'

@handler(PLEX_PATH, NAME, thumb=ICONS['default'])
def MainMenu():       

        oc = ObjectContainer()

        Updater(PLEX_PATH+'/updater', oc)

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
                key   = Callback(WantedMissing, page=1, pageSize=20),
                title = u'%s (%d)' % (L('wanted'), WantedMissingSize()),
                thumb = R(ICONS['wanted'])
        ))

        oc.add(DirectoryObject(
                key   = Callback(History),
                title = L('history'),
                thumb = R(ICONS['system'])
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

        oc = ObjectContainer()

        params = {'page':     page,
                  'pageSize': pageSize,
                  'sortKey': 'airDateUtc',
                  'sortDir': 'desc'}

        data = ApiRequest(method='get', endpoint='wanted/missing', params=params)

        for item in data['records']:
                airDate = Datetime.ParseDate(item['airDate'])
                images  = ProcessImages(item['series']['images'])
                summary = item['overview'] if 'overview' in item else "N/A"

                oc.add(DirectoryObject(
                        key   = Callback(EpisodeSearch, episodes=item['id']),
                        title = "%s, %s - %s" %(airDate.strftime('%b %d'), item['series']['title'], item['title']),
                        thumb = Callback(GetImage, url=images['poster']),
                        summary = summary
                ))

        if len(oc) >= pageSize:
                oc.add(NextPageObject(
                        key = Callback(WantedMissing, page=page+1, pageSize=pageSize)
                ))

        return oc

# Returns all series in your collection
@route(PLEX_PATH + '/series')
def Series():

        oc = ObjectContainer(no_cache=True)

        data = ApiRequest(method='get', endpoint='series')

        for item in data:
                title  = item['title']
                images = ProcessImages(item['images'])

                oc.add(DirectoryObject(
                        key   = Callback(Seasons, seriesId=item['id']),
                        title = title,
                        thumb = Callback(GetImage, url=images['poster'])
                ))

        return oc

# This may timeout on very large shows
@route(PLEX_PATH + '/seasons/{seriesId}', seriesId=int)
def Seasons(seriesId):

        oc = ObjectContainer()

        params = {"seriesId": seriesId}
        data   = ApiRequest(method='get', endpoint='episode', params=params, cacheTime=10)

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

        oc = ObjectContainer()

        params = {"seriesId": seriesId}
        data   = ApiRequest(method='get', endpoint='episode', params=params, cacheTime=10)

        for episode in list(reversed(data)):
                if episode['seasonNumber'] != seasonNumber:
                        continue

                epnum   = "S{:02d}E{:02d}".format(episode['seasonNumber'], episode['episodeNumber'])
                eptitle = episode['title']
                hasFile = episode['hasFile']
                epId    = episode['id']

                status = "✓" if hasFile else "-"

                key = Callback(Void) if hasFile else Callback(EpisodeSearch, episodes=epId)

                oc.add(DirectoryObject(
                        key   = key,
                        title = u'%s %s %s' %(epnum, status, eptitle),
                        thumb = R(ICONS['series'])
                ))

        return oc

# Sonarr searches its indexers and lists the available releases for episodeId. TODO: Make this do something
@route(PLEX_PATH + '/release/{episodeId}', episodeId=int)
def Release(episodeId):

        oc = ObjectContainer()

        params = {"episodeId": episodeId}
        data   = ApiRequest(method='get', endpoint="release", params=params)

        Log(data)

        for item in data:
                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = '%s - %s' % (item['indexer'], item['title']),
                        thumb = R(ICONS['series'])
                ))

        return oc

@route(PLEX_PATH + '/calendar')
def Calendar(startDate="", endDate=""):

        oc = ObjectContainer(no_cache=True)

        if not startDate or not endDate:
                now       = Datetime.Now()
                startDate = (now - Datetime.Delta(days=1)).strftime("%Y-%m-%d")
                endDate   = (now + Datetime.Delta(days=7)).strftime("%Y-%m-%d")

        start_dt = Datetime.ParseDate(startDate)
        end_dt   = Datetime.ParseDate(endDate)

        oc.add(DirectoryObject(
                key = Callback(Calendar, startDate = (start_dt - Datetime.Delta(days=7)).strftime("%Y-%m-%d"),
                                         endDate   = (end_dt   - Datetime.Delta(days=7)).strftime("%Y-%m-%d")),
                title = "<< Past week",
                thumb = R(ICONS['calendar'])
        ))
        oc.add(DirectoryObject(
                key = Callback(Calendar, startDate = (start_dt + Datetime.Delta(days=7)).strftime("%Y-%m-%d"),
                                         endDate   = (end_dt   + Datetime.Delta(days=7)).strftime("%Y-%m-%d")),
                title = "Next week >>",
                thumb = R(ICONS['calendar'])
        ))

        params = {"start": startDate,
                  "end":   endDate}
        data   = ApiRequest(method='get', endpoint='calendar', params=params)

        lastDate = ""
        for item in data:
                seriesType    = item['series']['seriesType']
                images        = ProcessImages(item['series']['images'])
                date          = Datetime.ParseDate(item['airDate'])
                hasFile       = item['hasFile']     if 'hasFile'     in item else False
                isDownloading = item['downloading'] if 'downloading' in item else False
                episodeId     = item['id']
                summary       = item['overview'] if 'overview' in item else "N/A"

                status = "✓" if hasFile else "-"
                status = "↓" if isDownloading else status

                epnum = 'S{:02d}E{:02d}'.format(item['seasonNumber'], item['episodeNumber']) if seriesType == 'standard' else ""
                title = "{time} {status} {series} - {epnum} {eptitle}".format(time = item['series']['airTime'], status=status, series = item['series']['title'], epnum=epnum, eptitle = item['title'])
                
                if date != lastDate:
                        oc.add(DirectoryObject(
                                key   = Callback(Void),
                                title = u'--[ %s ]------------------------------------------------------------------------' % date.strftime('%a, %b %d'),
                                thumb = R(ICONS['calendar'])
                        ))
                if hasFile:
                        oc.add(DirectoryObject(
                                key     = Callback(Void),
                                title   = u'%s' % title,
                                summary = u'%s' % summary,
                                thumb   = Callback(GetImage, url=images['poster']),
                                art     = Callback(GetImage, url=images['fanart']),
                        ))
                else:
                        oc.add(DirectoryObject(
                                key     = Callback(EpisodeSearch, episodes=episodeId),
                                title   = u'%s' % title,
                                summary = u'%s' % summary,
                                thumb   = Callback(GetImage, url=images['poster']),
                                art     = Callback(GetImage, url=images['fanart']),
                        ))

                lastDate = date

        return oc

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

        # Check the status
        data = ApiRequest(method='get', endpoint='command/%d' % data['id'])

        lastMessage = ""
        while data:
                time.sleep(0.2)
                data = ApiRequest(method='get', endpoint='command/%d' % data['id'])

                message = data['message'] if 'message' in data else ""
                if message != lastMessage:
                        oc.add(DirectoryObject(
                                key   = Callback(Void),
                                title = message,
                        ))
                lastMessage = message

                if data['state'] == 'completed':
                        break

        return oc

# sortKey = "series.title" or "date"
@route(PLEX_PATH + '/history', page=int, pageSize=int)
def History(page=1, pageSize=20, sortKey="date", sortDir="desc"):

        oc = ObjectContainer(no_cache=True)

        params = {"page":     page,
                  "pageSize": pageSize,
                  "sortKey":  sortKey,
                  "sortDir":  sortDir}
        data   = ApiRequest(method='get', endpoint='history', params=params)

        for item in data['records']:

                date = Datetime.ParseDate(item['date'])
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

        oc = ObjectContainer(no_cache=True)

        data = ApiRequest(method='get', endpoint='queue')

        for item in data:
                images    = ProcessImages(item['series']['images'])
                protocol  = item['protocol']
                status    = item['status']
                itemtitle = item['title']
                timeleft  = item['timeleft'] if 'timeleft' in item else "N/A"

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