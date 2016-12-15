#! python
# -*- coding: utf-8 -*-
"""
################################################################################
#
# processLog.py
#
#      process the www.geocaching.com logs for a given geocacher
#      generate a summary in XML format
#
# Copyright GarenKreiz at  geocaching.com or on  YouTube
# Auteur    GarenKreiz sur geocaching.com ou sur YouTube
#
# Licence:
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""

import re
import os
import sys
import datetime
import locale
import urllib2
import codecs
import StringIO
import gzip

# os.environ['LC_ALL'] = 'fr_FR.UTF-8'
# locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
locale.setlocale(locale.LC_ALL, '')

# default title and description of the logbook (should be in logbook_header.xml)
bookTitle = u"""<title>Titre à parametrer<br/> Customizable title</title>"""
bookDescription = u"""<description><![CDATA[%s]]>Description du journal - Logbook description - Fichier à modifier : logbook_header.xml - Modify file : logbook_header.xml]]></description>"""

class Logbook(object):  
    """
    Logbook : generate a list of logs with images for a geocacher
    """

    def __init__(self,
                 nameSourceFile, nameXmlFile="logbook.xml",
                 verbose=True, startDate=None, endDate=None, refresh=False, excluded=[]):
        self.nameSourceFile = nameSourceFile
        self.nameXmlFile = nameXmlFile
        self.fXML = codecs.open(nameXmlFile, "w", 'utf-8', buffering=0)
        self.verbose = verbose
        self.startDate = startDate
        self.endDate = endDate
        self.refresh = refresh
        self.excluded = excluded

    def processLogs(self):
        """
        analyse of the HTML page with all the logs of the geocacher
        local dump of the web page https://www.geocaching.com/my/logs.aspx?s=1
        """

        numberDaysSelected = 0          # number of processed dates
        numberLogSelected = 0           # number of processed logs
        numberDaySearch = 0             # number differents search days

        try:
            with codecs.open('logbook_header.xml', 'r', 'utf-8') as f:
                self.fXML.write(f.read())
        except:
            self.fXML.write('<?xml version="1.0" encoding="UTF-8"?>')
            self.fXML.write('<document>\n')
            self.fXML.write('<title><![CDATA[%s]]></title>\n' % bookTitle)
            self.fXML.write('<description>%s</description>\n' % bookDescription)

        listHeaderLog = self.searchHeaderLog()
        listHeaderLogSorted = sorted(listHeaderLog, key=lambda log: log['datelog'])
        previousDate = ''
        for logHeader in listHeaderLogSorted:
            # check if date is in the correct interval
            if logHeader['datelog'] != previousDate:
                numberDaySearch += 1
            if self.startDate and logHeader['datelog'] < self.startDate:
                continue
            if self.endDate and logHeader['datelog'] > self.endDate:
                continue
            numberLogSelected += 1
            if logHeader['datelog'] != previousDate:
                self.fXML.write('<date>%s</date>\n' % (self.formatDate(logHeader['datelog'])))
                numberDaysSelected += 1
            previousDate = logHeader['datelog']
            # building a local cache of the HTML page of each log
            # directory: Logs and 16 sub-directories based on the first letter
            url, dirLog = (('seek', 'Logs') if logHeader['naturelog'] == 'C' else ('track', 'LogsTB'))
            if self.refresh or not self.isFileData(dirLog, logHeader['idlog']):
                dataLogBody = self.loadLogFromUrl(url, dirLog, logHeader)
            elif self.isFileData(dirLog, logHeader['idlog']):
                dataLogBody = self.loadLogFromFile(dirLog, logHeader)
            if dataLogBody:
                # grabbing information from the log page
                self.parseLogBody(dataLogBody, logHeader)
        self.fXML.write('<source>Source : GarenKreiz/Geocaching-Journal @ GitHub (CC BY-NC 3.0 FR)</source>\n')
        self.fXML.write('</document>')
        self.fXML.close()
        print 'Logs: ', numberLogSelected, '/', len(listHeaderLog), 'Days:', numberDaysSelected, '/', numberDaySearch
        print 'Result file:', self.nameXmlFile

    def searchHeaderLog(self):
        listLogHeader = []
        with codecs.open(self.nameSourceFile, 'r', 'utf-8') as fIn:
            cacheData = fIn.read()
        tagTable = re.search('<table class="Table">(.*)</table>', cacheData, re.S).group(1)
        tagTr = re.finditer('<tr(.*?)</tr>', tagTable, re.S)
        listTr = [result.group(1) for result in tagTr]
        logNumber = 0
        for tr in listTr:
            td = re.finditer('<td>(.*?)</td>', tr, re.S)
            listTd = [result.group(1) for result in td]
            dateLog = self.normalizeDate(listTd[2].strip())
            typeLog = re.search('title="(.*)".*>', listTd[0]).group(1)
            idCache = re.search('guid=(.*?)"', listTd[3]).group(1)
            idLog = re.search('LUID=(.*?)"', listTd[5]).group(1)
            titleCache = re.search('</a> <a(.*)?\">(.*)</a>', listTd[3]).group(2).replace('</span>', '')
            natureLog = (u'C' if listTd[3].find('cache_details') > 1 else u'T')  # C for Cache and T for trackable

            # keeping the logs that are not excluded by -x option
            # keep = (True if typeLog.lower() in [item.lower() for item in self.excluded] else False)
            # test short string research exclude - ex : -x Write for Write note or -x Found for Found it - etc.
            keepLog = (False if len([excluded for excluded in self.excluded if excluded.lower() in typeLog.lower()]) else True)
            if keepLog and idLog != '':
                logNumber += 1
                listLogHeader.append({'datelog':dateLog, 'typelog':typeLog, 'idcache':idCache, 'idlog':idLog, 'titlecache':titleCache, 'naturelog':natureLog})
                if self.verbose:
                    print "(%s) %s|%s|%s|%s|%s|%s" % (logNumber, idLog, dateLog, idCache, titleCache, typeLog, natureLog)
        return listLogHeader
    
    def parseLogBody(self, dataLogBody, logHeader):
        """
        analyses the HTML content of a log page
        """

        text = ''
        listeImages = []
        titleCache = logHeader['titlecache']

        url, urlLog = (('seek/cache_', 'seek') if logHeader['naturelog'] == 'C' else ('track/', 'track'))
        if url == 'track/' and 'cache_details.aspx' in dataLogBody:
            # adding the name of the cache where the trackable is, if present in the log
            titleTb = re.search('cache_details.aspx\?guid=([^>]*)">(.*?)</a>', dataLogBody, re.S).group(2)
            titleCache = logHeader.titleCache + ' @ ' + titleTb
        self.fXML.write('<post><![CDATA[%s | http://www.geocaching.com/%sdetails.aspx?guid=%s |' % (titleCache, url, logHeader['idcache']))
        self.fXML.write('%s | http://www.geocaching.com/%s/log.aspx?LUID=%s]]></post>\n' % (logHeader['typelog'], urlLog, logHeader['idlog']))

        if '_LogText">' in dataLogBody:
            text = re.search('_LogText">(.*?)</span>', dataLogBody, re.S).group(1)
            text = re.sub('src="/images/', 'src="http://www.geocaching.com/images/', text)
            self.fXML.write('<text><![CDATA[%s]]></text>\n' % text)
        else:
            self.fXML.write('<text> </text>\n')
            print "!!!! Log unavailable", logHeader.idLog
            return

        if 'LogBookPanel1_GalleryList' in dataLogBody:  # if Additional images
            tagTable = re.search('<table id="ctl00_ContentBody_LogBookPanel1_GalleryList(.*?)</table>', dataLogBody, re.S).group(0)
            title = re.findall('<img alt=\'(.*?)\' src', tagTable, re.S)
            title = [re.sub(' log image', "", result) for result in title]
            url = re.findall('src="(.*?)" />', tagTable, re.S)
            url = [re.sub('log/.*/', "log/display/", result) for result in url]  # normalize form : http://img.geocaching.com/cache/log/display/*.jpg
            for index, tag in enumerate(url):
                panoraExist = self.isPanorama(title[index])
                listeImages.append((url[index], title[index], panoraExist))
            print '=> Log with %s images' % str(len(listeImages))
        elif 'LogBookPanel1_ImageMain' in dataLogBody:  # if single images
            urlTitle = re.search('id="ctl00_ContentBody_LogBookPanel1_ImageMain(.*?)href="(.*?)" target(.*?)span class="logimg-caption">(.*?)</span><span>', dataLogBody, re.S)
            panoraExist = self.isPanorama(urlTitle.group(4))
            listeImages.append((urlTitle.group(2), urlTitle.group(4), panoraExist))
            print '=> Log with one image'
        else:
            print u'!!!! Log without image', logHeader['idlog'], logHeader['datelog'], u'%r' % titleCache,'>>>', logHeader['typelog']

        # listeImages.sort(key=lambda e: e[2]) # panoramas are displayed after the other images - sort by field panoraExist
        if listeImages:
            self.fXML.write('<images>\n')
            for (img, caption, panoraExist) in listeImages:
                typeImage = ('pano' if panoraExist else 'image')
                # at this point, no information is available on the size of image
                # assume a standard format 640x480 (nostalgia of the 80's?)
                if typeImage == 'pano':
                    img = re.sub('/display/', '/', img)
                self.fXML.write("<![CDATA[<%s>%s<height>480</height><width>640</width><comment>%s</comment></%s>]]>\n" % (typeImage, img, caption, typeImage))
            self.fXML.write('</images>\n')

    # images with "panorama" or "panoramique" in the caption are supposed to be wide pictures
    def isPanorama(self, title):
        return (True if re.search('panoram', title, re.IGNORECASE) else False)

    def isFileData(self, dirLog, idLog):
        # LogsTB dedicated directory for TB logs as ID may be reused between TB and cache logs
        dirLog = dirLog + '/_%s_/' % idLog[0]
        if not os.path.isfile(dirLog+idLog) or self.refresh:
            if not os.path.isdir(dirLog):
                print "Creating directory "+dirLog
                os.makedirs(dirLog)
            return False
        else:
            return True

    def loadLogFromFile(self, dirLog, logHeader):
        dirLog = dirLog + '/_%s_/' % logHeader['idlog'][0]
        with codecs.open(dirLog+logHeader['idlog'], 'r', 'utf-8') as fr:
            if self.verbose:
                print "Loading for cache " + logHeader['titlecache']
            dataLogBody = fr.read()
        return dataLogBody

    def loadLogFromUrl(self, url, dirLog, logHeader):
        """
        download and save data from url
        """
        dirLog = dirLog + '/_%s_/' % logHeader.idLog[0]
        url = 'http://www.geocaching.com/' + url + '/log.aspx?LUID=' + logHeader.idLog
        print "Fetching log", url
        try:
            request = urllib2.Request(url)
            request.add_header('Accept-encoding', 'gzip')
            response = urllib2.urlopen(request, timeout=15)
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                dataLogBody = f.read().decode('utf-8')
            else:
                dataLogBody = response.read().decode('utf-8')
            print "Saving log file "+logHeader.idLog
            with codecs.open(dirLog+logHeader.idLog, 'w', 'utf-8') as fw:
                fw.write(dataLogBody)
        except (urllib2.HTTPError, urllib2.URLError), e:
            print "Error accessing log " + logHeader.idLog, e
            dataLogBody = None
        finally:
            response.close()
        return dataLogBody

    def formatDate(self, date):
        """
        format date in readable form, according to local settings
        """

        try:
            date = datetime.datetime.strptime(date, '%Y/%m/%d').strftime('%A %d %B %Y')
        except ValueError:
            date = datetime.datetime.strptime('2001/01/01', '%Y/%m/%d').strftime('%A %d %B %Y')
        date = date.replace(' 0', ' ')
        date = date.decode(locale.getpreferredencoding())
        return date

    def normalizeDate(self, date):
        """
        mormalize date in YYYY/MM/DD form
        """

        date = re.sub('[-. ]+', '/', date)
        date = re.sub('/+$', '', date)
        (y, m, d) = date.split('/')
        if int(m) > 12:
            print "Date format month/day/year not supported. Choose another format in the web site preferences (day/month/year)."
        if int(d) > 1969:
            # dd.mm.yyyy
            d, y = y, d
        elif int(y) < 1970:
            # dd.mm.yy
            d, y = y, int(d)+2000
        date = '%02d/%02d/%02d' % (int(y), int(m), int(d))
        return date.decode('utf-8')

if __name__ == '__main__':
    def usage():
        print 'Usage: python processLogs.py [-q|--quiet] geocaching_logs.html logbook.xml'
        print '    or python processLogs.py [-q|--quiet] geocaching_logs.html logbook.html'
        print ''
        print '   geocaching_logs.html'
        print '       dump of the web page containing all you logs (HTML only)'
        print '       sauvegarde de la page contenant tous vos logs (HTML uniquement)'
        print '   logbook.xml'
        print '       content of all log entries with reference to pictures'
        print '       contenu de tous les logs avec references aux images'
        print '   logbook.html'
        print '       web page with all logs and images (using xml2print.py)'
        print '       page web avec tous les logs et images (utilise xml2print.py)'
        print ''
        print '   -q|--quiet'
        print '       less verbose console output'
        print '       execution du programme moins verbeuse'
        print '   -s|--start startDate'
        print '       start processing log at date startDate (included, format YYYY/MM/DD)'
        print '       commence le traitement des logs a partir de la date startDate incluse (format AAAA/MM/JJ)'
        print '   -e|--end endDate'
        print '       stop processing log after date endDate (format YYYY/MM/DD)'
        print '       arrete le traitement des logs apres la date endDate (format AAAA/MM/JJ)'
        print '   -r|--refresh'
        print '       refresh local cache of logs (to use when the log was changed or pictures were added)'
        print '       rafraichit la version locale des journaux (a utiiser si des modifications ont ete faites ou des photos ont ete ajoutees'
        print '   -x|--exclude'
        print '       exclude a given log type, can be repeated (for example "-x update -x disable")'
        print '       exclusion de certains types de log, par recherche de chaine de caractere (par exemple "-x update -x disable")'

        sys.exit()

    import getopt

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hrqs:e:x:", ['help', 'refresh', 'quiet', 'start', 'end', 'exclude'])
    except getopt.GetoptError:
        usage()

    verbose = True
    startDate = None
    endDate = None
    refresh = False
    excluded = []

    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt == "-q":
            verbose = False
        elif opt == "-r":
            refresh = True
        elif opt == "-s":
            if len(arg.split('/')) != 3:
                print "!!! Bad start date format, use YYYY/MM/DD"
                print "!!! Format de date de debut faux, utiliser AAAA/MM/JJ"
                sys.exit(1)
            startDate = arg
        elif opt == "-e":
            if len(arg.split('/')) != 3:
                print "Bad end date format, use YYYY/MM/DD"
                print "Format de date de fin faux, utiliser AAAA/MM/JJ"
                sys.exit(1)
            endDate = arg
        elif opt == "-x":
            excluded.append(arg)

    print "Excluded:", excluded

    if len(args) == 2:
        if re.search(".xml", args[0], re.IGNORECASE):
            xmlFile = args[0]
        elif re.search(".xml", args[1], re.IGNORECASE):
            xmlFile = args[1]
        else:
            xmlFile = "logbook.xml"

        # firt phase : from Groundspeak HTML to XML
        if re.search(".htm[l]*", args[0], re.IGNORECASE):
            Logbook(args[0], xmlFile, verbose, startDate, endDate, refresh, excluded).processLogs()

        # second phase : from XML to generated HTML
        if re.search(".htm[l]*", args[1], re.IGNORECASE):
            import xml2print
            xml2print(xmlFile, args[1], printing=False, groupPanoramas=True)
        print "That's all folks!"
    else:
        usage()
