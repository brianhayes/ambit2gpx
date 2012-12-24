import os
import xml.dom.minidom
import math
import getopt
import sys

def radian2degree(radian):
    return radian * 180.0 / math.pi
    
def converttime(time):
    return time *1.0

def childElements(parent):   
    elements = []
    for child in parent.childNodes:
        if child.nodeType != child.ELEMENT_NODE:
            continue
        elements.append(child)
    return elements

class AmbitXMLParser(object):
    __root = None
    __outputfile = None
    def __init__(self, xml_node, suunto, noalti, altibaro, nohr, outputfile, lastdistance, first):
        assert isinstance(xml_node,xml.dom.Node)
        assert xml_node.nodeType == xml_node.ELEMENT_NODE
        self.__root = xml_node
        self.__outputfile = outputfile
        self.__altibaro = altibaro
        self.__noalti = noalti
        self.__suunto = suunto
        self.__altitude = None
        self.__latitude = None
        self.__longitude = None
        self.__hr = None
        self.__nohr = nohr
        self.__lastdistance = lastdistance
        self.__first = first
        self.__nb_samples_parsed = 0
        
    def extension(self,hr):
        if (hr == None or self.__nohr == True):
            return ""
        return """
<extensions> 
    <gpxtpx:TrackPointExtension> 
        <gpxtpx:hr>{hr}</gpxtpx:hr> 
    </gpxtpx:TrackPointExtension> 
</extensions>
""".format(hr=hr)           

    def __parse_sample(self, sample,lastdistance, first):
        llatitude = None
        llongitude = None
        time = None
        distance = None
        self.__nb_samples_parsed += 1
        if self.__nb_samples_parsed % 100 == 0:
            sys.stdout.write(".")
            if self.__nb_samples_parsed % (80*100) == 0:
                sys.stdout.write("\n")
        for node in childElements(sample):
            key = node.tagName
            if key == "Latitude":
                if not self.__suunto:
                    llatitude = radian2degree(float(node.firstChild.nodeValue))
                else:
                    self.__latitude = radian2degree(float(node.firstChild.nodeValue))
            if key == "Longitude":
                if not self.__suunto:
                    llongitude = radian2degree(float(node.firstChild.nodeValue))
                else:
                    self.__longitude = radian2degree(float(node.firstChild.nodeValue))
            if key == "UTC":
                time = node.firstChild.nodeValue
            if key == "HR":
                self.__hr = int((float(node.firstChild.nodeValue))*60+0.5)
            if key == "Altitude":
                if self.__noalti:
                    self.__altitude = 0
                elif self.__altibaro:
                    self.__altitude = node.firstChild.nodeValue
            if key == "GPSAltitude":
                if self.__noalti:
                    self.__altitude = 0
                elif not self.__altibaro:
                    self.__altitude = node.firstChild.nodeValue
            if key == "Distance":
                distance = converttime(float(node.firstChild.nodeValue))
        if (not self.__suunto) and llatitude != None and llongitude != None:
            print >>self.__outputfile, """
<trkpt lat="{latitude}" lon="{longitude}">
    <ele>{altitude}</ele>
    <time>{time}</time>
    {extension}  
</trkpt>
""".format(latitude=llatitude, longitude=llongitude, altitude=self.__altitude, time=time, extension=self.extension(self.__hr))
        elif self.__suunto and self.__first and self.__latitude != None and self.__longitude != None:
            self.__first = False
            print >>self.__outputfile, """
<trkpt lat="{latitude}" lon="{longitude}">
    <ele>{altitude}</ele>
    <time>{time}</time>
    {extension}  
</trkpt>
""".format(latitude=self.__latitude, longitude=self.__longitude, altitude=self.__altitude, time=time, extension=self.extension(self.__hr))
        elif self.__suunto and self.__latitude != None and self.__longitude != None and distance > self.__lastdistance:
            self.__lastdistance = distance
            print >>self.__outputfile, """
<trkpt lat="{latitude}" lon="{longitude}">
    <ele>{altitude}</ele>
    <time>{time}</time>
    {extension}  
</trkpt>
""".format(latitude=self.__latitude, longitude=self.__longitude, altitude=self.__altitude, time=time, extension=self.extension(self.__hr))

    def __parse_samples(self, samples, lastdistance, first):
        for node in childElements(samples):
            key = node.tagName
            if key == "sample":
                self.__parse_sample(node,lastdistance, first)
      
    def execute(self):   
        print >>self.__outputfile,'<?xml version="1.0" encoding="UTF-8" standalone="no" ?>'
        print >>self.__outputfile,"""
<gpx 
xmlns="http://www.topografix.com/GPX/1/1"
xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1" 
creator="ambit2gpx" version="1.1"
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd">
 <metadata>
    <link href="http://code.google.com/p/ambit2gpx/">
      <text>Ambit2GPX</text>
    </link>
   </metadata>
  <trk>
    <trkseg>  
"""              
        root = self.__root
        lastdist = self.__lastdistance
        fir = self.__first
        for node in childElements(root):
            key = node.tagName
            if key == "samples":
                self.__parse_samples(node, lastdist, fir)
                
        print >>self.__outputfile,"""
    </trkseg>        
  </trk>
</gpx>
"""

def usage():
    print """
ambit2gpx [--suunto] [--noalti] [--altibaro] [--nohr] filename
Creates a file filename.gpx in GPX format from filename in Suunto Ambit XML format.
If option --suunto is given, only retain GPS fixes retained by Suunto distance algorithm.
If option --noalti is given, elevation will be put to zero.
If option --altibaro is given, elevation is retrieved from altibaro information. The default is to retrieve GPS elevation information.
If option --nohr is given, hr data will not generated. Useful for instance if size of output file matters.
"""

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "ha", ["help", "suunto", "noalti", "altibaro", "nohr"])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)
    if len(sys.argv[1:]) == 0:
        usage()
        sys.exit(2)
    output = None
    verbose = False
    suunto = False
    noalti = False
    altibaro = False
    nohr = False
    lastdistance = 0
    first = True
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s", "--suunto"):
            suunto = True
        elif o in ("-n", "--noalti"):
            noalti = True
        elif o in ("-a", "--altibaro"):
            altibaro = True
        elif o in ("--nohr"):
            nohr = True
        else:
            assert False, "unhandled option"
    # ...
    
    filename = args[0]
    (rootfilename, ext) = os.path.splitext(filename)
    if (ext == ""):
        filename += ".xml"
    if (not os.path.exists(filename)):
        print >>sys.stderr, "File {0} doesn't exist".format(filename)
        sys.exit()
    file = open(filename)
    file.readline() # Skip first line
    filecontents = file.read()
    file.close()
    
    print "Parsing file {0}".format(filename)
    doc = xml.dom.minidom.parseString('<?xml version="1.0" encoding="utf-8"?><top>'+filecontents+'</top>')
    assert doc != None
    top = doc.getElementsByTagName('top')
    assert len(top) == 1    
    print "Done."
    
    outputfilename = rootfilename+ '.gpx'
    outputfile = open(outputfilename, 'w')
    print "Creating file {0}".format(outputfilename)
    AmbitXMLParser(top[0], suunto, noalti, altibaro, nohr, outputfile, lastdistance, first).execute()
    outputfile.close()
    print "\nDone."
        
if __name__ == "__main__":
    main()
