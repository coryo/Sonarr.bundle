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

####################################################################################################
# Main
####################################################################################################                 
def Start():

        ObjectContainer.title1 = NAME
        HTTP.CacheTime  = 0
        HTTP.User_Agent = 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36'
        HTTP.Headers['X-Api-Key'] = Prefs['apikey']
        Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
        Plugin.AddViewGroup("Images",  viewMode="Pictures", mediaType="items")

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

# for retrieving images from the server with the apikey header
@route(PLEX_PATH + '/getimage')
def GetImage(url):

        try:
                data = HTTP.Request(url=url, headers={"X-Api-Key": Prefs['apikey']}, cacheTime=CACHE_1WEEK).content
                return DataObject(data, 'image/jpeg')
        except:
                return Redirect(R(ICONS['default']))                

@route(PLEX_PATH + '/serieslist')
def SeriesList():

        oc = ObjectContainer(no_cache=True)

        url     = API_URL.format(server=Prefs['address'], endpoint="Series")
        headers = {"X-Api-Key": Prefs['apikey']}

        data = JSON.ObjectFromURL(url, headers=headers)

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

        url     = API_URL.format(server=Prefs['address'], endpoint="Episode") + "?seriesId=%d" % seriesId
        headers = {"X-Api-Key": Prefs['apikey']}

        data = JSON.ObjectFromURL(url, headers=headers)

        for episode in data:
                epnum   = "S{:02d}E{:02d}".format(episode['seasonNumber'], episode['episodeNumber'])
                eptitle = episode['title']
                hasFile = episode['hasFile']

                status = "✓" if hasFile else "-"

                oc.add(DirectoryObject(
                        key   = Callback(Void),
                        title = u'%s %s %s' %(epnum, status, eptitle),
                        thumb = R(ICONS['series'])
                ))

        return oc       

@route(PLEX_PATH + '/calendar')
def Calendar(startDate="", endDate=""):

        oc = ObjectContainer(no_cache=True)

        if not startDate:
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

        url     = API_URL.format(server=Prefs['address'], endpoint="Calendar")
        headers = {"X-Api-Key": Prefs['apikey']}
        params  = {"start": startDate,
                   "end":   endDate}

        data = JSON.ObjectFromURL(url+"?"+urllib.urlencode(params), headers=headers)

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
                                thumb   = Resource.ContentsOfURLWithFallback(images['poster'], fallback=R(ICONS['default']))
                        ))
                else:
                        oc.add(DirectoryObject(
                                key     = Callback(EpisodeSearch, episodes=episodeId),
                                title   = u'%s' % title,
                                summary = u'%s' % summary,
                                thumb   = Resource.ContentsOfURLWithFallback(images['poster'], fallback=R(ICONS['default']))
                        ))

                lastDate = date

        return oc

@route(PLEX_PATH + '/EpisodeSearch/{episodes}')
def EpisodeSearch(episodes):

        oc = ObjectContainer()

        apiurl  = API_URL.format(server=GetServer(), endpoint="command")
        headers = {"X-Api-Key": Prefs['apikey']}
        params  = {"name": "EpisodeSearch",
                   "episodeIds": episodes.split(',')}

        # Sonarr wants JSON encoded post body, plex wants to urlencode it
        post_req = urllib2.Request(url=apiurl, data=JSON.StringFromObject(params), headers=headers)
        data     = JSON.ObjectFromString(urllib2.urlopen(post_req).read())
        Log("POST... " + str(data))

        # Get the status of the job
        data = JSON.ObjectFromURL(url=apiurl + "/%d" % data['id'], headers=headers) 
        Log("GET... " + str(data))

        lastMessage = ""
        while data['state'] != 'completed':
                data    = JSON.ObjectFromURL(url=apiurl + "/%d" % data['id'], headers=headers)
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

        apiurl  = API_URL.format(server=GetServer(), endpoint="History")
        params  = {"page":     page,
                   "pageSize": pageSize,
                   "sortKey":  "date",
                   "sortDir":  "desc"}
        headers = {"X-Api-Key": Prefs['apikey']}

        data = JSON.ObjectFromURL(url=apiurl+"?"+urllib.urlencode(params), headers=headers)

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

        apiurl  = API_URL.format(server=GetServer(), endpoint="Queue")
        headers = {"X-Api-Key": Prefs['apikey']}

        data = JSON.ObjectFromURL(url=apiurl, headers=headers)

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

# A route to nowhere
@route(PLEX_PATH + '/void')
def Void():

        return ObjectContainer()

def GetServer():

        return Prefs['address'] if not Prefs['address'].endswith("/") else Prefs['address'][:-1]