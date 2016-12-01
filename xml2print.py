# -*- coding: utf-8 -*-

from xml.sax import make_parser, handler
import codecs
import re
import sys

class XmlHandler(handler.ContentHandler):
    tag = "" #previous tag name
    breakCache =False

    def __init__(self, logbookName):
        self.numberDays = 0
        self.numberLogs = 0
        try:
            self.fw = codecs.open(logbookName, 'w', 'utf-8', buffering = 0)
        except IOError, e:
            print e
            
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
            self.numberDays += 1
        elif name == "post":
            self.post()     
            self.numberLogs += 1
        elif name == "text":
            self.text()       
        elif name == "description":
            self.description()
        elif name == "images":
            self.images()            

    def title(self):
        buffeur = '<!DOCTYPE html>\n'
        buffeur += '<head>\n'
        buffeur += '<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />\n'
        buffeur += '<meta content="IE=EmulateIE7" http-equiv="X-UA-Compatible" />\n'
        buffeur += '<meta content="true" name="MSSmartTagsPreventParsing" />\n'
        buffeur += '<!-- Generated by xml2print.py from Garenkreiz -->\n'
        buffeur += '<script language="JavaScript">\n'
        buffeur += '<!--\n'
        buffeur += 'var newwindow;\n'
        buffeur += 'function popstatic(url,windowName)\n'
        buffeur += '{\n'
        buffeur += '// newwindow=window.open(url,windowName,\'toolbar=no,status=no,menubas=no\');\n'
        buffeur += 'newwindow=window.open(url,windowName,\'toolbar=no,scrollbars=yes,status=no,menubar=no,location=no\');\n'
        buffeur += 'newwindow.resizeTo(screen.width-20,screen.height-20)\n'
        buffeur += 'newwindow.moveTo(10,10);\n'
        buffeur += 'if (window.focus) {newwindow.focus()}\n'
        buffeur += '}\n'
        buffeur += '//-->\n'
        buffeur += '</script>\n'
        buffeur += '<title>%s</title>\n'% self.current_content
        buffeur += '<link rel="stylesheet" type="text/css" href="logbook.css" media="all" />\n'
        buffeur += '</head>\n'
        buffeur += '<body>\n'
        buffeur += '<div class="header">\n'
        fields = self.current_content.split("|")
        buffeur += '<h1><a href="%s" target="_blank">%s</a></h1>\n' %(fields[1], fields[0])
        self.fw.write(buffeur)        

    def description(self):
        buffeur = '<p class="description">%s</p>\n'%self.current_content
        buffeur += '</div>\n' #div class header
        buffeur += '<div class="main">\n'
        self.fw.write(buffeur)

    def date(self):
        buffeur = '<div class="date">\n'
        buffeur += '<h2 class="date-header">%s</h2>\n'%self.current_content
        buffeur += '</div>\n'
        self.fw.write(buffeur)

    def post(self):
        buffeur =''
        if XmlHandler.breakCache == True:
            buffeur = '<div class="post-banner"></div>\n'
            XmlHandler.breakCache = False
        fields = self.current_content.split('|')
        buffeur += '<div class="post-entry">\n'
        buffeur += '<h3 class="post-title">\n'
        buffeur += '<div class="alignleft"><a href="%s" target="_blank">%s</a></div>\n'%(fields[1], fields[0])
        buffeur += '<div class="alignright"><a href="%s">%s</a></div>\n'%(fields[3], fields[2])
        buffeur += '<div style="clear: both;" />\n'
        buffeur += '</h3>\n'
        self.fw.write(buffeur)

    def text(self):
        buffeur = self.current_content
        buffeur += '</div>\n' #<div>class="post-entry
        self.fw.write(buffeur)

    def images(self):
        data = self.current_content.strip('\n').split('\n')
        breakLineMaster = (2 if len(data) == 4 else 3) # 2 column if number pictures = 4 
        buffeur = '<div>\n'
        buffeur += '<table class="table-pictures">\n' #master table
        buffeur += '<tbody>\n'
        buffeur += '<tr><td>\n'
        buffeur = self.childTable(data, buffeur, breakLineMaster)
        buffeur += '</td></tr>\n'
        buffeur += '</tbody>\n'              
        buffeur += '</table>\n' #master table
        buffeur += '</div>\n'
        self.fw.write(buffeur)

    def childTable(self, data, buffeur, breakLineMaster):
        counterImage = 0        
        for index, image in enumerate(data):
            counterImage += 1
            match =  re.search('image>(.*?)<(.*)<comment>(.*?)</comment>', image, re.S)
            caption  = match.group(3)
            pictureScr =  match.group(1)
            pictureHttp = pictureScr.replace("/display","")  
            buffeur += '<table class="picture" style="">\n' #child table
            buffeur += '<tr>\n<td>\n'
            buffeur += '<a href="javascript:popstatic(\'%s\',\'.\');"><img  src="%s" /></a>\n'%(pictureHttp, pictureScr)
            buffeur += '</td></tr>\n'
            buffeur += '<tr><td class="caption">%s</td></tr>\n'%caption
            buffeur += '</table>' #child table
            if (index + 1) %breakLineMaster  == 0: # create second line main table
                buffeur += '</td></tr><tr><td>' # break line master table
            elif counterImage < len(data): #if not last image
                buffeur +='</td><td>' 
                counterImage = 0    
        return buffeur    

    def source(self):
        buffeur = ('</div>\n') #<div class="main"
        buffeur += ('<div>\n')
        buffeur += ('<h2 class="footer">%s</h2>\n'%self.current_content)
        buffeur += ('</div>\n')
        buffeur += ('</html>')
        self.fw.write(buffeur)        
        self.fw.close()
        print 'Number days : %s - Number logs : %s'%(self.numberDays, self.numberLogs)

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
            printing = True #option non implémentée
        elif opt == "-g":
            groupPanoramas = True #option non implémentée

    if len(args) == 2:
        parser = make_parser()
        b = XmlHandler(args[1])
        parser.setContentHandler(b)
        try:
            parser.parse(args[0])
        except IOError, e:
            print e            
        print "That's all, folks!"
    else:
        usage()