#!python
# -*- coding: utf-8 -*-
"""
################################################################################
# xml2print.py
#
#     transforms an XML description of a logbook or blog intro HTML
#
#     tags : title, description, date, post, text, image, pano
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
import sys
import string

maxRow = 3   # number of pictures in a row (less than 4)

headerStart = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<meta content="IE=EmulateIE7" http-equiv="X-UA-Compatible">
<meta content="true" name="MSSmartTagsPreventParsing">
<!-- Generated by xml2print.py from Garenkreiz -->

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
"""

headerMiddle = """
<link rel="stylesheet" type="text/css" href="logbook.css" media="all">
</head>
<body>
<div class="header">
<h1>%s</h1>
"""

headerEnd = """
<p class="description"><i>%s</i></p>
</div> <!-- header -->
<div class="main">
"""

dateFormat = '<div class="date"><h2 class="date-header">%s</h2><div class="post-entry">'
postBegin = '<h3 class="post-title">'
postMiddle = '</h3>'
postBanner = '<div class="post-banner"></div><div class="post-entry">'
postEnd = '</div>  <!--// class:post-entry //-->'
dateEnd = '</div>  <!--// class:date //-->'
htmlEnd = '</body></html>'

pictureFormatTemplate = """
<table class="picture"><tbody>%s
<tr><td><img class="%s" src="%s"/></td></tr>
<tr><td class="caption">%s</td></tr>
%s</tbody></table>
"""

fOut = None


def cleanText(textInput, allTags=True):
    """
    cleaning text from HTML formatting
    """
    resu = re.sub('</*(tbody|table|div|text)[ /]*>', ' ', textInput)
    resu = re.sub('</*div>'                        , '',  resu)
    resu = re.sub('<div[^>]*>'                     , '',  resu)
    resu = re.sub('[\n\r]*'                        , '',  resu)
    resu = re.sub('  *'                            , ' ', resu)
    if allTags:
        resu = re.sub('<[^>]*>', '', resu)
    return resu


def flushImgTable(pictures):
    """
    end of a row of images
    """

    rowCount = 0       # current number of images in row
    
    panoramas = []
    
    fOut.write('<table class="table-pictures"><tr>')
    for (format, image, comment, width, height) in pictures:
        comment = re.sub('&pad;', '', comment)
        if format == 'panorama' and rowCount > 0 or rowCount == maxRow:
            # start a new row of pictures
            fOut.write('</tr></table>')
            fOut.write('<table class="table-pictures"><tr>')
            rowCount = 0
        rowCount = (maxRow if format == 'panorama' else rowCount + 1)
        fOut.write('<td>')
            
        # specific to geocaching logs : open a full sized view of picture
        imageFullSize = re.sub('https://img.geocaching.com/cache/log/display/', 'https://img.geocaching.com/cache/log/', image)
        popupLink = '<a href="javascript:popstatic(\'%s\',\'.\');">'%imageFullSize
        fOut.write(pictureFormatTemplate % (popupLink, format, image, comment, '</a>'))
        comment = re.sub('<br>', '', comment)
        fOut.write('</td>')
    fOut.write('</tr></table>')

def flushText(text):
    """
    flushing text as HTML paragraph
    """

    if text:
        if '<p>' not in text[0:10]:
            text = '<p>'+text+'</p>'
        fOut.write(text)


def processFile(fichier, printing=False):
    """
    analyse of a description file in XML and generate an HTML file
    """

    firstDate = True
    pictures = []
    processingPost = False

    print "Processing", fichier
    f = open(fichier, 'r')
    text = ''

    fOut.write(headerStart)

    l = f.readline().strip()
    while l <> '':
        # analyse of the XML tag
        l = l.strip()
        tag = re.sub('>.*', '>', l)

        if tag in ['<image>','<pano>','<post>','<date>','</text>']:
            flushText(text)
            text = ''
        if pictures <> [] and tag not in ['<image>']:
            flushImgTable(pictures)
            pictures = []
            
        if tag == '<image>' or tag == '<pano>':
            # parsing image item
            # <image>foo.jpg<height>480</height><width>640</width><comment>Nice picture</comment></image>
            # <pano>foo.jpg<height>480</height><width>1000</width><comment>Nice panorama</comment></image>
            # displaying images in tables
            line = re.sub('<[^>]*>', '|', l)
            try:
                imgDesc = line.split('|')
            except Exception, msg:
                print '!!!!!!!!!!!!! Exception: bad image format:', msg, line
            if len(imgDesc) == 4:
                (_, image, comment, _) = imgDesc
            elif len(imgDesc) == 9:
                (_, image, height, _, width, _, comment, _, _) = imgDesc
            else:
                print '!!!!!!!!!!!!! Bad image format:', line
            if tag == '<pano>':
                pictures.append(('panorama', image, comment, width, height))
            elif height > width:
                pictures.append(('portrait', image, comment, width, height))
            else:
                pictures.append(('landscape', image, comment, width, height))

        elif tag == '<title>':
            # title of the logbook
            l = re.sub('</*title>', '', l)
            title = l.split('|')
            fOut.write('<title>%s</title>\n' % cleanText(title[0], True))
            if len(title) == 2:
                # the title has 2 parts : a text | an URL
                titleText = '<a href="%s" target="_blank">%s</a>' % (title[1], title[0])
            else:
                fOut.write('<title>%s</title>\n' % cleanText(l, True))
                titleText = title[0]
            fOut.write(headerMiddle % titleText)

        elif tag == '<description>':
            # description of the logbook
            fOut.write(headerEnd % cleanText(l))

        elif tag == '<date>':
            # new date in the logbook
            if firstDate is False:
                fOut.write(postEnd + dateEnd)
            firstDate = False
            processingPost = False

            date = cleanText(l)
            if date <> '':
                date = string.upper(date[0])+date[1:]
            fOut.write(dateFormat % date)
            (image, text, width, height) = ('', '', 0, 0)

        elif tag == '<post>':
            # new post title : left text | url | right text | url
            if processingPost:
                fOut.write(postEnd + postBanner) # banner between 2 posts
            processingPost = True
            post = cleanText(l)
            print 'Post:', re.sub('\|.*', '', post)

            # <post>left title|left url|right title|right url</post>
            elements = post.split('|')
            if len(elements) > 1:
                post = '<a href="' + elements[1] + '" target="_blank">' + elements[0].strip() + '</a>'
                if len(elements) > 2:
                    post = '<div class="alignleft">' + post + '</div>'
                    log = elements[2].strip()
                    if len(elements) > 3:
                        log = '<a href="' + elements[3] + '" target="_blank">' + log + '</a>'
                    post = post + '<div class="alignright">' + log + '</div>'
            else:
                post = elements[0].strip()
            fOut.write(postBegin + post + postMiddle)

        elif tag == '<text>':
            # list of paragraphs
            fOut.write('<div style="clear: both;"></div>')
            if text <> '':
                text = text +'</p><p>'
            text = text + cleanText(l, False)

        elif tag == '<split/>':
            # splitting image table
            print 'Splitting table'

        elif tag == '<page/>':
            # start a new page : to be used to optimize the printing version
            if printing:
                fOut.write('<div class="page-break"  style="page-break-before:always;"></div>\n')

        elif tag in ['<image>', '</image>', '<pano>', '</pano>', '</text>']:
            # already processed
            pass
        else:
            text = text + cleanText(l, False)

        l = f.readline()

    if pictures <> []:
        # the logbook ends with images
        flushImgTable()

    fOut.write(postEnd + htmlEnd)


def xml2print(xmlInput, htmlOutput, printing=False):
    """
    main function of module : generation of an HTML file from an XML file
    """

    global fOut
    
    fOut = open(htmlOutput, 'w')
    processFile(xmlInput, printing)
    fOut.close()
    print "Result file:", htmlOutput


if __name__ == "__main__":
    def usage():
        """
        print help on program
        """

        print 'Usage: python xml2print.py [-p|--printing] logbook.xml logbook.html'
        sys.exit()

    import getopt
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hp", ['help', 'printing'])
    except getopt.GetoptError:
        usage()

    printing = False
    for opt, arg in opts:
        if opt == '-h':
            usage()
        elif opt == "-p":
            printing = True

    if len(args) == 2:
        try:
            xml2print(args[0], args[1], printing)
        except Exception, msg:
            print "Problem:",msg
        print "That's all, folks!"
    else:
        usage()
