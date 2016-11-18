#! python
# -*- coding: utf-8 -*-
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

import re
import os
import sys
import time
import locale
import urllib2


#os.environ['LC_ALL'] = 'fr_FR.UTF-8'
#locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
locale.setlocale(locale.LC_ALL, '')

# default title and description of the logbook (should be in logbook_header.xml)
bookTitle="""<title>Titre a parametrer<br/> Customizable title</title>"""
bookDescription="""<description>Description du journal - Logbook description - Fichier a modifier : logbook_header.xml - Modify file : logbook_header.xml</description>"""

class Logbook:

    def __init__(self,
                 fNameInput, fNameOutput="logbook.xml",
                 verbose=True, localImages=False, startDate = None, endDate = None, refresh = False, excluded = []):
        self.fNameInput = fNameInput 
        self.fXML = open(fNameOutput,"w")
        self.fNameOutput = fNameOutput
        self.verbose = verbose
        self.localImages = localImages
        self.startDate = startDate
        self.endDate = endDate
        self.refresh = refresh
        self.excluded = excluded

        self.nDates = 0          # number of processed dates
        self.nLogs = 0           # number of processed logs

    # analyses the HTML content of a log page
    def parseLog(self,dataLog,dateLog,idLog,idCache,titleCache,typeLog,natureLog):
        text = ''
        images = {}
        #print 'Log:',idLog,idCache,titleCache,typeLog

        if natureLog == 'C':
            url = 'seek/cache_'
            urlLog='seek'
        else:
            url = 'track/'
            urlLog = 'track'
            # adding the name of the cache where the trackable is, if present in the log
            tBegin = dataLog.find('cache_details.aspx')
            if tBegin > 0:
                tBegin = dataLog.find('>',tBegin)
                tEnd = dataLog.find('<',tBegin)
                titleCache = titleCache + ' @ '+ dataLog[tBegin+1:tEnd]
        self.fXML.write('<post>%s | http://www.geocaching.com/%sdetails.aspx?guid=%s |'%(titleCache,url,idCache))
        self.fXML.write('%s | http://www.geocaching.com/%s/log.aspx?LUID=%s</post>\n'%(typeLog,urlLog,idLog))

        tBegin = dataLog.find('_LogText">')
        if tBegin > 0:
            tBegin += len('_LogText">')
            tEnd = dataLog.find('</span>',tBegin)
            if tEnd > 0:
                text = dataLog[tBegin:tEnd]
        else:
            self.fXML.write('<text> </text>\n')
            print "!!!! Log unavailable",idLog
            return
        
        if self.localImages:
            text = re.sub('src="/images/','src="Images/',text)
        else:
            text = re.sub('src="/images/','src="http://www.geocaching.com/images/',text)
        self.fXML.write('<text>%s</text>\n'%text)

        listPanoramas=[]
        listImages=[]

        #g = dataLog.find('_GalleryList"',tEnd)
        g = dataLog.find('LogImagePanel',tEnd)
        if g > 0:
            p = dataLog.find('<img ',g+1)
            while p > 0:
                # finding the URL of the image
                sBegin = dataLog.find('src="',p)
                sEnd = dataLog.find('"',sBegin+5)
                src = dataLog[sBegin+5:sEnd]
                if not re.search('(cache|track)/log/',src):
                    print '!!!! Bad image:',src
                    p = dataLog.find('<img ',p+4)
                    continue

                # normalize form : http://img.geocaching.com/cache/log/display/*.jpg
                if self.localImages:
                    src = re.sub('.*(thumb|display)','Images',src)     # to use if there is a local cache of images
                else:
                    src = re.sub('thumb','display',src)                # to use to access images on geocaching site

                # finding the caption of the image
                patternB = re.compile('<(small|span|strong)[^>]*>')
                patternE = re.compile('</(small|span|strong)[^>]*>')
                searchResult = patternB.search(dataLog,sEnd)
                tBegin = searchResult.end()                  # begin of tag
                tEnd = patternE.search(dataLog,tBegin).start()  # end of tag
                caption = re.sub('<[^>]*>','',dataLog[tBegin:tEnd])
                if caption.find('Click image to view original') <> -1:
                    searchResult = patternB.search(dataLog,tEnd+2)
                    tBegin = searchResult.end()                 # begin of tag
                    tEnd = patternE.search(dataLog,tBegin).start()  # end of tag
                    caption = re.sub('<[^>]*>','',dataLog[tBegin:tEnd])
                caption = caption.strip(' \n\r\t')

                # images with "panorama" or "panoramique" in the captin are supposed to be wide pictures
                if re.search('panoram', caption, re.IGNORECASE):
                    src = re.sub('/log/display/','/log/',src)     # use full size image for panorama

                    if not (src,caption) in listPanoramas:
                        listPanoramas.append((src,caption))
                else:
                    if not src in listImages:
                        # at this point, no information is available on the size of image
                        # assume a standard format 640x480 (nostalgia of the 80's?)
                        self.fXML.write("<image>%s<height>480</height><width>640</width><comment>%s</comment></image>\n"%(src,caption))
                        listImages.append(src)
                try:
                    images[idLog].append((src,caption))
                except:
                    images[idLog] = ((src,caption))

                # goto next image
                p = dataLog.find('<img alt=',p+1)

            # panoramas are displayed after the other images
            # each on a separate line
            if listPanoramas <> []:
                for (src,caption) in listPanoramas:
                    self.fXML.write("<pano>%s<height>480</height><width>640</width><comment>%s</comment></pano>\n"%(src, caption))

        self.nLogs += 1

        # identifying logs without image
        try:
            images[idLog][0]
        except:
            print "!!!! Log without image:",idLog,dateLog,titleCache,'>>>',typeLog

    # analyse of the HTML page with all the logs of the geocacher
    # local dump of the web page https://www.geocaching.com/my/logs.aspx?s=1
    def processLogs(self):
        try:
            with open('logbook_header.xml', 'r') as f:
                self.fXML.write(f.read())
        except:
            self.fXML.write('<title>'+bookTitle+'</title>\n')
            self.fXML.write('<description>'+bookDescription+'</description>\n')

        logsCount = 0
        days = {}

        idLog = None
        with open(self.fNameInput,'r') as fIn:
            cacheData = fIn.read()
        tagTable = re.search('<table class="Table">(.*)</table>',cacheData, re.S|re.M).group(1)
        tagTr = re.finditer('<tr(.*?)</tr>',tagTable, re.S)
        listTr = [result.group(1) for result in tagTr]
        for tr in listTr:
            td = re.finditer('<td>(.*?)</td>',tr, re.S)
            listTd = [result.group(1) for result in td]
            dateLog =  self.__normalizeDate(listTd[2].strip())
            typeLog =  re.search('title="(.*)".*>',listTd[0]).group(1)
            idCache = re.search('guid=(.*?)"',listTd[3]).group(1)
            idLog = re.search('LUID=(.*?)"',listTd[5]).group(1)
            titleCache =  re.search('</a> <a(.*)?\">(.*)</a>',listTd[3]).group(2).replace('</span>','')
            natureLog =  ('C' if listTd[3].find('cache_details') > 1 else 'T') # C for Cache and T for trackable
            # keeping the logs that are not excluded by -x option
            #keep = (True if typeLog.lower() in [item.lower() for item in self.excluded] else False)
            #test short string research exclude - ex : -x Write for Write note or -x Found for Found it - etc. 
            keep = (True if len([excluded for excluded in self.excluded if excluded.lower() in typeLog.lower()]) else False)
            if not keep and idLog <> '':
                logsCount += 1
                try:
                    days[dateLog].append((idLog,idCache,titleCache,typeLog,natureLog))
                except:
                    days[dateLog] = [(idLog,idCache,titleCache,typeLog,natureLog)]
                if self.verbose:
                    print "%s|%s|%s|%s|%s|%s"%(idLog,dateLog,idCache,titleCache,typeLog,natureLog)
        dates = days.keys()
        dates.sort()
        for dateLog in dates:
            # check if date is in the correct interval
            if self.startDate and dateLog < self.startDate:
                continue
            if self.endDate and dateLog > self.endDate:
                continue
            self.nDates += 1
            self.fXML.write('<date>%s</date>\n'%self.__formatDate(dateLog))

            dayLogs = days[dateLog]
            dayLogs.reverse()
            for (idLog,idCache,titleCache,typeLog,natureLog) in dayLogs:
                # logId, cacheId or tbID, title, type, nature
                # building a local cache of the HTML page of each log
                # directory: Logs and 16 sub-directories based on the first letter

                # LogsTB dedicated directory for TB logs as ID may be reused between TB and cache logs
                url, dirLog = (('seek', 'Logs') if natureLog == 'C' else ('track', 'LogsTB'))
                dirLog = dirLog + '/_%s_/'%idLog[0]
                if not os.path.isfile(dirLog+idLog) or self.refresh:
                    if not os.path.isdir(dirLog):
                        print "Creating directory "+dirLog
                        os.makedirs(dirLog)
                    url = 'http://www.geocaching.com/'+url+'/log.aspx?LUID='+idLog
                    print "Fetching log",url
                    dataLog = urllib2.urlopen(url).read()
                    print "Saving log file "+idLog
                    with open(dirLog+idLog,'w') as fw:
                        fw.write(dataLog)
                else:
                    with open(dirLog+idLog,'r') as fr:
                        dataLog = fr.read()
                # grabbing information from the log page
                self.parseLog(dataLog,dateLog,idLog,idCache,titleCache,typeLog,natureLog)

        self.fXML.write('<date>Source : GarenKreiz/Geocaching-Journal @ GitHub (CC BY-NC 3.0 FR)</date>\n')
        print 'Logs: ',self.nLogs,'/',logsCount, 'Days:',self.nDates,'/',len(dates)
        print 'Result file:', self.fNameOutput

    def __formatDate(self, date):
        strTime = date+" 00:00:01Z"
        t=0
        try:
            t = int(time.mktime(time.strptime(strTime, "%Y/%m/%d %H:%M:%SZ")))
        except:
            pass
        date = time.strftime('%A %d %B %Y', time.localtime(t))
        date = date.decode(locale.getpreferredencoding()).encode('utf8')
        date = re.sub(' 0',' ', date)
        return date
    
    def __normalizeDate(self, date):
        date = re.sub('[-. ]+','/', date)
        date = re.sub('/+$','', date)
        (y,m,d) = date.split('/')
        if int(m) > 12:
            print "Date format month/day/year not supported. Choose another format in the web site preferences (day/month/year)."
        if int(d) > 1969:
            # dd.mm.yyyy
            d,y = y,d
        elif int(y) < 1970:
            # dd.mm.yy
            d,y = y,int(d)+2000
        date = '%02d/%02d/%02d'%(int(y), int(m), int(d))
        return date    
    
if __name__=='__main__':
    def usage():
        print 'Usage: python processLogs.py [-q|--quiet] [-l|--local-images] geocaching_logs.html logbook.xml'
        print '    or python processLogs.py [-q|--quiet] [-l|--local-images] geocaching_logs.html logbook.html'
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
        print '   -l|--local-images'
        print '       use local images in directory Images (previously downloaded for example using "wget")'
        print '       utilisation d\'une copie locale des images dans le repertoire Images (telechargees par exemple avec "wget")'
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
        opts, args = getopt.getopt(sys.argv[1:],"hrqls:e:x:", ['help','refresh','quiet','local-images','start','end','exclude'])
    except getopt.GetoptError:
        usage()

    verbose = True
    localImages = False
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
        elif opt == "-l":
            localImages = True
        elif opt == "-s":
            if len(arg.split('/')) <> 3:
                print "!!! Bad start date format, use YYYY/MM/DD"
                print "!!! Format de date de debut faux, utiliser AAAA/MM/JJ"
                sys.exit(1)
            startDate = arg
        elif opt == "-e":
            if len(arg.split('/')) <> 3:
                print "Bad end date format, use YYYY/MM/DD"
                print "Format de date de fin faux, utiliser AAAA/MM/JJ"
                sys.exit(1)
            endDate = arg
        elif opt == "-x":
            excluded.append(arg)

    print "Excluded:",excluded

    if len(args) == 2:
        if re.search(".xml", args[0], re.IGNORECASE):
            xmlFile = args[0]
        elif re.search(".xml", args[1], re.IGNORECASE):
            xmlFile = args[1]
        else:
            xmlFile = "logbook.xml"

        # firt phase : from Groundspeak HTML to XML
        if re.search(".htm[l]*", args[0], re.IGNORECASE):
            Logbook(args[0],xmlFile,verbose,localImages,startDate,endDate,refresh,excluded).processLogs()

        # second phase : from XML to generated HTML
        if re.search(".htm[l]*",args[1], re.IGNORECASE):
            import xml2print
            xml2print.xml2print(xmlFile,args[1])
        print "That's all folks!"
    else:
        usage()
