# -*- coding: utf-8 -*-

from xml.sax import make_parser, handler
import codecs
import re
import sys

class XmlHandler(handler.ContentHandler):
    tag = "" #previous tag name
    breakCache =False

    def __init__(self, logbookName):
        self.fw = codecs.open(logbookName, 'w', 'utf-8', buffering = 0)

    def startElement(self, name, attrs):
        self.current_content = ""
        if name == 'post' and XmlHandler.tag == 'text' or  XmlHandler.tag == 'images': #if same day
            XmlHandler.breakCache = True
        if name == 'post' and XmlHandler.tag == 'date' : #if new day
            XmlHandler.breakCache = False                        
        XmlHandler.tag = name 
        
    def characters(self, content):
        self.current_content += content

    def endElement(self, name):
        if name == "title":
            self.title()
        elif name == "source":
            self.source()   
        elif name == "date":
            self.date()     
        elif name == "post":
            self.post()     
        elif name == "text":
            self.text()       
        elif name == "description":
            self.description()
        elif name == "images":
            self.images()            

    def title(self):
        self.fw.write(u"""<!DOCTYPE html>
                    <html>
                    <head>
                    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
                    <meta content="IE=EmulateIE7" http-equiv="X-UA-Compatible" />
                    <meta content="true" name="MSSmartTagsPreventParsing" />
                    <!-- Generated by xml2print.py from Garenkreiz -->\n
                    <script language="JavaScript">
                    <!--
                    var newwindow;
                    function popstatic(url,windowName)
                    {
                        // newwindow=window.open(url,windowName,'toolbar=no,status=no,menubas=no');
                        newwindow=window.open(url,windowName,'toolbar=no,scrollbars=yes,status=no,menubar=no,location=no');
                        newwindow.resizeTo(screen.width-20,screen.height-20)
                        newwindow.moveTo(10,10);
                        if (window.focus) {newwindow.focus()}
                    }
                    //-->
                    </script>
                    """)
        self.fw.write('<title>%s</title>'% self.current_content)
        fields = self.current_content.split("|") 
        self.fw.write(u"""
                    <link rel="stylesheet" type="text/css" href="logbook.css" media="all" />
                    </head>
                    <body>
                    <div class="header">
                    <h1><a href="%s" target="_blank">%s</a></h1>\n""" %(fields[1], fields[0]))     

    def description(self):
        self.fw.write(u"""<p class="description">%s</p>\n</div>\n<div class="main">\n"""%self.current_content)

    def date(self):
        self.fw.write(u"""<div class="date">\n<h2 class="date-header">%s</h2>\n</div>\n"""%self.current_content)

    def post(self):
        if XmlHandler.breakCache == True:
            self.fw.write('<div class="post-banner"></div>\n')
            XmlHandler.breakCache = False
        fields = self.current_content.split('|')
        self.fw.write(u"""<div class="post-entry">\n<h3 class="post-title">
        <div class="alignleft">
        <a href="%s" target="_blank">%s</a>
        </div>
        <div class="alignright">
        <a href="%s">%s</a>
        </div>\n<div style="clear: both;" />\n</h3>\n"""%(fields[1], fields[0], fields[3], fields[2]))

    def text(self):
        self.fw.write(u"""%s</div>\n""" %self.current_content)

    def images(self):
        data = self.current_content.strip('\n').split('\n')
        breakLineNumber = (2 if len(data) <= 4 else 3) # 2 column if number pictures <= 4 
        self.fw.write('<div>\n<table class="table-pictures">\n<tbody>\n<tr><td>')
        counterImage = 0        
        for index, image in enumerate(data):
            counterImage += 1
            match =  re.search('image>(.*?)<(.*)<comment>(.*?)</comment>', image, re.S)
            caption  = match.group(3)
            pictureScr =  match.group(1)
            pictureHttp = pictureScr.replace("/display","")  
            self.fw.write(u'''\n<table class="picture" style="">\n<tr>\n<td>
                        <a href="javascript:popstatic('%s','.');"><img  src="%s" /></a></td></tr>
                        <tr><td class="caption">%s</td></tr>\n</table>'''%(pictureHttp, pictureScr, caption))
            if (index + 1) %breakLineNumber  == 0: # create second line main table
                self.fw.write('</td></tr><tr><td>')
            elif counterImage < len(data): #if not last image
                self.fw.write('</td><td>') 
                counterImage = 0               
        self.fw.write('</td></tr>\n</tbody>\n</table>\n</div>\n')

    def source(self):
        self.fw.write(u'''</div>\n<div>\n<h2 class="footer">%s</h2>\n</div>\n</html>'''%self.current_content)

if __name__ == "__main__":
    def usage():
        """
        print help on program
        """

        print 'Usage: python xml2print.py [-p|--printing] [-g|--groupPanoramas] logbook.xml logbook.html'
        sys.exit()

    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hpg", ['help', 'printing', 'groupPanoramas'])
    except getopt.GetoptError:
        usage()

    printing = False #option non implémentée
    groupPanoramas = False
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt == "-p":
            printing = True
        elif opt == "-g":
            groupPanoramas = True

    if len(args) == 2:
        try:
            #xml2print(args[0], args[1], printing, groupPanoramas)
            parser = make_parser()
            b = XmlHandler(args[1])
            parser.setContentHandler(b)
            parser.parse(args[0])            
        except Exception, msg:
            print "Problem:",msg
        print "That's all, folks!"
    else:
        usage()