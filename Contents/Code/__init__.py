import urllib, urllib2, time

NAME       = 'Sonarr'
PLEX_PATH  = '/applications/sonarr'

API_URL  = "{server}/api/{endpoint}"

ICONS = {
        "default": "sonarr-content-icon.png",
        "series":  "icon-series.png",
        "calendar": "icon-calendar.png",
        "activity": "icon-activity.png",
        "wanted":   "icon-wanted.png",
        "settings": "icon-settings.png",
        "system":   "icon-system.png",
}

def ApiRequest(method, endpoint, params=None):

        url     = API_URL.format(server=Prefs['address'], endpoint=endpoint)
        headers = {"X-Api-Key": Prefs['apikey']}
        params  = params if params else {}

        try:
                if method == 'post':
                        post_req = urllib2.Request(url=url, data=JSON.StringFromObject(params), headers=headers)
                        data     = JSON.ObjectFromString(urllib2.urlopen(post_req).read())
                        return data
                elif method =='get':
                        data = JSON.ObjectFromURL(url+"?"+urllib.urlencode(params), headers=headers)
                        return data
                else:
                        return {}
        except: 
                return {}

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
                data = HTTP.Request(url=url, headers={"X-Api-Key": Prefs['apikey']}, cacheTime=CACHE_1WEEK).content
                return DataObject(data, 'image/jpeg')
        except:
                return Redirect(R(ICONS['default']))     

####################################################################################################
# Main
####################################################################################################                 
def Start():

        ObjectContainer.title1 = NAME
        HTTP.CacheTime  = 0
        HTTP.User_Agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36'

@handler(PLEX_PATH, NAME)
def MainMenu():       

        oc = ObjectContainer()

        oc.add(DirectoryObject(
                key   = Callback(SeriesList),
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
                title = L('queue'),
                thumb = R(ICONS['activity'])
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

@route(PLEX_PATH + '/serieslist')
def SeriesList():

        oc = ObjectContainer(no_cache=True)

        data = ApiRequest(method='get', endpoint='series')

        for item in data:
                title  = item['title']
                images = {imageType['coverType']: GetServer() + "/api"+ imageType['url'] for imageType in item['images']}

                oc.add(DirectoryObject(
                        key   = Callback(Episode, seriesId=item['id']),
                        title = title,
                        thumb = Callback(GetImage, url=images['poster'])
                ))

        return oc

@route(PLEX_PATH + '/episode', seriesId=int)
def Episode(seriesId):

        oc = ObjectContainer()

        params = {"seriesId": seriesId}
        data   = ApiRequest(method='get', endpoint='episode', params=params)

        for episode in data:
                epnum   = "S{:02d}E{:02d}".format(episode['seasonNumber'], episode['episodeNumber'])
                eptitle = episode['title']
                hasFile = episode['hasFile']
                epId    = episode['id']

                status = "✓" if hasFile else "-"

                oc.add(DirectoryObject(
                        key   = Callback(Release, episodeId=epId),
                        title = u'%s %s %s' %(epnum, status, eptitle),
                        thumb = R(ICONS['series'])
                ))

        return oc

@route(PLEX_PATH + '/release')
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
                images        = {imageType['coverType']: imageType['url'] for imageType in item['series']['images']}
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
                                thumb   = Resource.ContentsOfURLWithFallback(images['poster'], fallback=R(ICONS['default'])),
                                art     = Resource.ContentsOfURLWithFallback(images['fanart'])
                        ))
                else:
                        oc.add(DirectoryObject(
                                key     = Callback(EpisodeSearch, episodes=episodeId),
                                title   = u'%s' % title,
                                summary = u'%s' % summary,
                                thumb   = Resource.ContentsOfURLWithFallback(images['poster'], fallback=R(ICONS['default'])),
                                art     = Resource.ContentsOfURLWithFallback(images['fanart'])
                        ))

                lastDate = date

        return oc

@route(PLEX_PATH + '/EpisodeSearch/{episodes}')
def EpisodeSearch(episodes):

        oc = ObjectContainer()

        # Send the command
        params = {"name": "EpisodeSearch",
                  "episodeIds": episodes.split(',')}
        data   = ApiRequest(method='post', endpoint='command', params=params)

        time.sleep(0.2)

        # Check the status
        data = ApiRequest(method='get', endpoint='command/%d' % data['id'])

        lastMessage = ""
        while data['state'] != 'completed':
                data = ApiRequest(method='get', endpoint='command/%d' % data['id'])

                message = data['message'] if 'message' in data else ""

                if message != lastMessage:
                        oc.add(DirectoryObject(
                                key   = Callback(Void),
                                title = message,
                        ))
                lastMessage = message
                time.sleep(0.2)

        return oc

@route(PLEX_PATH + '/history', page=int, pageSize=int)
def History(page=1, pageSize=20):

        oc = ObjectContainer(no_cache=True)

        params = {"page":     page,
                  "pageSize": pageSize,
                  "sortKey":  "date",
                  "sortDir":  "desc"}
        data   = ApiRequest(method='get', endpoint='history', params=params)

        for item in data['records']:

                date = Datetime.ParseDate(item['date'])
                oc.add(DirectoryObject(
                        key = Callback(Void),
                        title = u'%s - [%s] - %s' % (date.strftime("%b %d, %H:%M"), item['eventType'], item['sourceTitle']),
                ))

        if len(oc) >= pageSize:
                oc.add(NextPageObject(
                        key = Callback(History, page=page+1, pageSize=pageSize)
                ))

        return oc

@route(PLEX_PATH + '/queue')
def Queue():

        oc = ObjectContainer(no_cache=True)

        data = ApiRequest(method='get', endpoint='queue')

        for item in data:
                Log(item)

                protocol  = item['protocol']
                status    = item['status']
                itemtitle = item['title']

                title = "{p} - {s} - {t}".format(p=protocol, s=status, t=itemtitle)
                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = title,
                        thumb = R(ICONS['series'])
                ))

        return oc