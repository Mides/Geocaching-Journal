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
            self.constructTitle()
        elif name == "source":
            self.constructSource()   
        elif name == "date":
            self.constructDate()     
            self.numberDays += 1
        elif name == "post":
            self.constructPost()     
            self.numberLogs += 1
        elif name == "text":
            self.constructText()       
        elif name == "description":
            self.constructDescription()
        elif name == "images":
            self.constructMasterTable()            

    def constructTitle(self):
        fields = self.current_content.split("|")        
        buffeur = ("<!DOCTYPE html>\n"
                   "<head>\n"
                   "<meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\" />\n"
                   "<meta content=\"IE=EmulateIE7\" http-equiv=\"X-UA-Compatible\" />\n"
                   "<meta content=\"true\" name=\"MSSmartTagsPreventParsing\" />\n"
                   "<!-- Generated by xml2print.py from Garenkreiz -->\n"
                   "<script language=\"JavaScript\">\n"
                   "<!--\n"
                   "var newwindow;\n"
                   "function popstatic(url,windowName)\n"
                   "{\n"
                   "// newwindow=window.open(url,windowName,\'toolbar=no,status=no,menubas=no\');\n"
                   "newwindow=window.open(url,windowName,\'toolbar=no,scrollbars=yes,status=no,menubar=no,location=no\');\n"
                   "newwindow.resizeTo(screen.width-20,screen.height-20)\n"
                   "newwindow.moveTo(10,10);\n"
                   "if (window.focus) {newwindow.focus()}\n"
                   "}\n"
                   "//-->\n"
                   "</script>\n"
                   "<title>%s</title>\n"
                   "<link rel=\"stylesheet\" type=\"text/css\" href=\"logbook.css\" media=\"all\" />\n"
                   "</head>\n"
                   "<body>\n"
                   "<div class=\"header\">\n"
                   "<h1><a href=\"%s\" target=\"_blank\">%s</a></h1>\n") %(self.current_content, fields[1], fields[0])
        self.fw.write(buffeur)        

    def constructDescription(self):
        #</div> class header
        buffeur = ("<p class=\"description\">%s</p>\n"
                   "</div>\n"
                   "<div class=\"main\">\n") % self.current_content
        self.fw.write(buffeur)

    def constructDate(self):
        buffeur = ("<div class=\"date\">\n"
                   "<h2 class=\"date-header\">%s</h2>\n"
                   "</div>\n") % self.current_content
        self.fw.write(buffeur)

    def constructPost(self):
        buffeur =''
        if XmlHandler.breakCache == True:
            buffeur = '<div class="post-banner"></div>\n'
            XmlHandler.breakCache = False
        fields = self.current_content.split('|')
        buffeur += ("<div class=\"post-entry\">\n"
                    "<h3 class=\"post-title\">\n"
                    "<div class=\"alignleft\"><a href=\"%s\" target=\"_blank\">%s</a></div>\n"
                    "<div class=\"alignright\"><a href=\"%s\">%s</a></div>\n"
                    "<div style=\"clear: both;\" />\n"
                    "</h3>\n") % (fields[1], fields[0], fields[3], fields[2])
        self.fw.write(buffeur)

    def constructText(self):
        buffeur = self.current_content
        buffeur += '</div>\n' #<div>class="post-entry
        self.fw.write(buffeur)

    def constructMasterTable(self):
        data = self.current_content.strip('\n').split('\n')
        breakLineMaster = (2 if len(data) == 4 else 3) # 2 column if number pictures = 4
        #<table class="table-pictures"> master table 
        buffeur = ("<div>\n"
                   "<table class=\"table-pictures\">\n"
                   "<tbody>\n"
                   "<tr><td>\n")
        buffeur = self.constructChildTable(data, buffeur, breakLineMaster)
        buffeur += ("</td></tr>\n"
                    "</tbody>\n"              
                    "</table>\n"
                    "</div>\n")
        self.fw.write(buffeur)

    def constructChildTable(self, data, buffeur, breakLineMaster):
        counterImage = 0        
        for index, image in enumerate(data):
            counterImage += 1
            match =  re.search('image>(.*?)<(.*)<comment>(.*?)</comment>', image, re.S)
            caption  = match.group(3)
            pictureScr =  match.group(1)
            pictureHttp = pictureScr.replace("/display","")
            #<table class="picture" style  child table
            buffeur += ("<table class=\"picture\" style="">\n" 
                        "<tr>\n<td>\n"
                        "<a href=\"javascript:popstatic(\'%s\',\'.\');\"><img  src=\"%s\" /></a>\n"
                        "</td></tr>\n"
                        "<tr><td class=\"caption\">%s</td></tr>\n"
                        "</table>")%(pictureHttp, pictureScr, caption)
            if (index + 1) %breakLineMaster  == 0: # create second line main table
                buffeur += '</td></tr><tr><td>' # break line master table
            elif counterImage < len(data): #if not last image
                buffeur +='</td><td>' 
                counterImage = 0    
        return buffeur    

    def constructSource(self):
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