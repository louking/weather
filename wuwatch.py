#!/usr/bin/python
###########################################################################################
#   wuwatch - display weather underground data
#
#   Date		Author		Reason
#   ----		------		------
#   10/02/12	Lou King	Create
#   11/05/12    Lou King    Add window persistence
#   11/16/12    Lou King    Add set station form
#   11/29/12    Lou King    Fix test code
#   12/06/12    Lou King    Add persistence of WeatherStation object
#
#   Copyright 2012 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###########################################################################################
'''
wuwatch - display weather underground data
==============================================
'''

# standard
import pdb
import argparse
import urllib2
import xml.etree.ElementTree as ET
from cStringIO import StringIO
import sys
import string

# pypi
import pygeocoder
import motionless

# github

# other
import wx   # http://wxpython.org/download.php - 2.9 minimum
from wx.lib.agw.persist.persistencemanager import PersistenceManager, PersistentObject
from wx.lib.agw.persist.persist_handlers import AbstractHandler, TLWHandler
import wx.lib.agw.hyperlink as hl
from wundergroundLogo_4c_horz import wulogo

# home grown
import version
from loutilities import wxextensions

# full weather string is in same order as this
# xml key is before caret (^), display format is after
DISPLAYFORMAT = ('' +
    'location/full^{0},' +
    'station_id^Station ID: {0},' +
    'observation_time^{0},' +
    'temperature_string^Temperature: {0},' +
    'wind_string^Wind Speed: {0},' +
    'dewpoint_string^Dew Point: {0},' +
    'windchill_string^Wind Chill: {0},' +
    'pressure_string^Barometric Pressure: {0},' +
    'precip_1hr_string^Precipitation (current hour): {0},' +
    'precip_today_string^Precipitation (today): {0},' +
    'credit^{0}'
       # NOTE: no comma or + for last string
    )
DISPLAYKEYS = [f.split('^')[0] for f in DISPLAYFORMAT.split(',')]
DISPLAYFORMATS = [f.split('^')[1] for f in DISPLAYFORMAT.split(',')]
DISPLAYFIELDS = dict(zip(DISPLAYKEYS,DISPLAYFORMATS))

WUAPIKEY = '4290fe192dd34983'

wuaccess = True         # set by options on startup

########################################################################
def SetDcContext(memDC, font=None, color=None):
########################################################################
# from http://wiki.wxpython.org/WorkingWithImages#Write_Text_to_a_Bitmap
    if font:
        memDC.SetFont( font )
    else:
        memDC.SetFont( wx.NullFont )

    if color:
        memDC.SetTextForeground( color )

########################################################################
class WeatherStationHandler(AbstractHandler):
########################################################################
    """
    handle persistence for WeatherStation object
    """

    #----------------------------------------------------------------------
    def __init__(self, pObj):
    #----------------------------------------------------------------------
        """
        handle persistence for WeatherStation object

        :param pObj: PersistenceObject object
        """

        self.pObj = pObj
        self.wxstn = pObj.GetWindow()
        AbstractHandler.__init__(self,pObj)


    #----------------------------------------------------------------------
    def GetKind(self):
    #----------------------------------------------------------------------
        """
        WeatherStation
        """

        return 'WeatherStation'

    #----------------------------------------------------------------------
    def Save(self):
    #----------------------------------------------------------------------
        """
        save WeatherStation's state
        """

        self.wxstn.SaveValue('stnname',self.wxstn.wundergroundstation)

    #----------------------------------------------------------------------
    def Restore(self):
    #----------------------------------------------------------------------
        """
        restore WeatherStation's state
        """

        self.wxstn.wundergroundstation = self.wxstn.RestoreValue('stnname')

########################################################################
class WeatherStation(PersistentObject):
########################################################################
    #----------------------------------------------------------------------
    def __init__(self, station=None):
    #----------------------------------------------------------------------
        """
        return a WeatherStation object

        :param station: name of wunderground station, or None (default 'KMDIJAMS2')
        """

        PersistentObject.__init__(self,self,WeatherStationHandler)

        self.debug = False

        self.wxstring = ''

        self.pm = PersistenceManager()
        self.pm.Register(self,persistenceHandler=WeatherStationHandler)
        check = self.pm.Restore(self)

        # set wundergroundstation to default if it hasn't been defined by self.pm.Restore
        try:
            stn = self.wundergroundstation
            if stn is None:
                raise AttributeError
        except AttributeError:
            self.wundergroundstation = 'KMDIJAMS2'

    #----------------------------------------------------------------------
    def shutdown(self):
    #----------------------------------------------------------------------
        """
        remember state upon deletion
        """

        self.pm.SaveAndUnregister(self)

    #----------------------------------------------------------------------
    def GetName(self):
    #----------------------------------------------------------------------
        """
        override PersistentObject.GetName -- return name of this object
        """
        return 'WeatherStation'

    #----------------------------------------------------------------------
    def setstation(self,station):
    #----------------------------------------------------------------------
        """
        set the configured wunderground station

        :param station: name of wunderground station
        """
        self.wundergroundstation = station
        self.pm.Save(self)

    #----------------------------------------------------------------------
    def gettemp(self):
    #----------------------------------------------------------------------
        """
        get temperature from configured weather underground station

        :rtype: int with current temperature
        """

        # get data from wunderground
        wu = urllib2.urlopen('http://api.wunderground.com/weatherstation/WXCurrentObXML.asp?ID={0}'.format(self.wundergroundstation))
        wuxml = wu.readlines()
        wu.close()
        tree = ET.fromstringlist(wuxml)

        # pull out full weather string
        self.wxstring = ''
        fields = list(DISPLAYKEYS) # make a copy
        while len(fields) > 0:
            field = fields.pop(0)

            ###
            subfields = field.split('/')
            thisel = tree.copy()
            while len(subfields) > 0:
                subfield = subfields.pop(0)
                thisel = thisel.find(subfield)
            self.wxstring += DISPLAYFIELDS[field].format(thisel.text)
            ###
            # self.wxstring += DISPLAYFIELDS[field].format(tree.find(field).text)

            if len(fields) > 0:
                self.wxstring += '\n'

        self.url = tree.find('ob_url').text

        if self.debug:
            pdb.set_trace()
            self.debug = False

        temp = int(round(float(tree.find('temp_f').text)))
        return temp

    #----------------------------------------------------------------------
    def getwxstring(self):
    #----------------------------------------------------------------------
        """
        get the last full weather string

        :rtype: string containing weather data
        """
        return self.wxstring

    #----------------------------------------------------------------------
    def geturl(self):
    #----------------------------------------------------------------------
        """
        get the url string

        :rtype: string containing url
        """
        return self.url

########################################################################
class IconText:
########################################################################

    #----------------------------------------------------------------------
    def __init__(self, initial=''):
    #----------------------------------------------------------------------
        """
        return an IconText object

        :param initial: initial text for display
        """

        self.icon = self.settext(initial)

    #----------------------------------------------------------------------
    def settext(self,text):
    #----------------------------------------------------------------------
        """
        set the text for display

        :param text: text to display
        """
        self.text = text
        bmp = wx.EmptyBitmap(16,16)

        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.Brush("black"))
        SetDcContext(dc,color="white")    # sets font and color to defaults
        dc.Clear()

        try:
            dc.DrawText(text, 0, 0)
        except :
            pass

        dc.SelectObject( wx.NullBitmap )
        bmp.SetMaskColour("black")  # black is transparent -- needs to be outside of dc context selection

        self.icon = wx.EmptyIcon()
        self.icon.CopyFromBitmap(bmp)

        return self.icon

    #----------------------------------------------------------------------
    def geticon(self):
    #----------------------------------------------------------------------
        """
        get the latest ocon

        :rtype: wx.Icon with latest text
        """
        return self.icon

########################################################################
class WxDisplay(wx.Frame):
########################################################################
    LOGOBORDER = 16

    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        self.formname = 'weather details'
        wx.Frame.__init__(self, None, wx.ID_ANY, self.formname, size=(350,200),
            style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR)
        self.panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_ICONIZE, self.onIconize)
        self.Bind(wx.EVT_MAXIMIZE, self.onMaximize)

        self.debug = False

        self.vbox = wx.BoxSizer(wx.VERTICAL)
##        self.SetSizer(self.vbox)      # causes python to crash, issue #10

        self.st = wx.StaticText(self.panel)
        self.vbox.Add(self.st,border=8)

        self.url = hl.HyperLinkCtrl(self.panel)
        self.Bind(hl.EVT_HYPERLINK_LEFT, self.onClick)
        self.vbox.Add(self.url)

        self.logo = wx.StaticBitmap(self.panel,bitmap=wx.EmptyBitmap(1,1))
        self.vbox.Add(self.logo,flag=wx.ALL,border=self.LOGOBORDER)
        self.logoimg = wulogo.GetImage()

        self.panel.SetSizerAndFit(self.vbox)

        self.Fit()

        self.SetName(self.formname)
        self.pm = PersistenceManager()
        self.pm.Register(self,persistenceHandler=TLWHandler)
        check = self.pm.Restore(self)
        if self.debug: print ('Position at WxDisplay.__init__ is {0}'.format(self.GetPosition()))

        self.Show(False)    # start without showing form

    #----------------------------------------------------------------------
    def onClick(self, evt):
    #----------------------------------------------------------------------
        """
        Follow URL link in self.url
        """
        url = self.url.GetURL()
        wx.LaunchDefaultBrowser(url)

    #----------------------------------------------------------------------
    def shutdown(self):
    #----------------------------------------------------------------------

        if self.debug: print ('Position at WxDisplay.shutdown is {0}'.format(self.GetPosition()))
        self.pm.SaveAndUnregister(self)

    #----------------------------------------------------------------------
    def onIconize(self, evt):
    #----------------------------------------------------------------------
        """
        Leave only the systray icon
        """
        #self.onClose(evt)
        if self.debug: print ('Position at WxDisplay.onIconize is {0}'.format(self.GetPosition()))
        self.Show(False)

    #----------------------------------------------------------------------
    def onMaximize(self, evt):
    #----------------------------------------------------------------------
        """
        Show the frame
        """
        if self.debug: print ('Position at WxDisplay.onMaximize is {0}'.format(self.GetPosition()))
        self.Show(True)

    #----------------------------------------------------------------------
    def onClose(self, evt):
    #----------------------------------------------------------------------
        """
        Destroy the taskbar icon and the frame
        """
        self.Show(False)

    #----------------------------------------------------------------------
    def settext(self, text):
    #----------------------------------------------------------------------
        """
        set text for the form

        :param text: text to put into the form
        """

        self.st.SetLabel(text)

    #----------------------------------------------------------------------
    def seturl(self, url):
    #----------------------------------------------------------------------
        """
        set url for the form

        :param url: url to put into the form
        """

        self.url.SetURL(url)
        self.url.SetLabel('wunderground details')

    #----------------------------------------------------------------------
    def setlogoandfit(self):
    #----------------------------------------------------------------------
        """
        set text for the form

        :param url: url to put into the form
        """

        self.logo.SetBitmap(wx.EmptyBitmap(1,1))

        self.panel.SetSizerAndFit(self.vbox)

        panelwidth = float(self.panel.GetMinWidth())
        scalefactor = (panelwidth-self.LOGOBORDER*2)/self.logoimg.Width
        scaledimg = self.logoimg.Scale(self.logoimg.Width*scalefactor, self.logoimg.Height*scalefactor, wx.IMAGE_QUALITY_HIGH)
        self.logo.SetBitmap(wx.BitmapFromImage(scaledimg))

        self.panel.SetSizerAndFit(self.vbox)
        self.Fit()

########################################################################
class UpdateStnHandler(TLWHandler):
########################################################################
    """
    handle persistence for WeatherStation object
    """

    #----------------------------------------------------------------------
    def __init__(self, pObj):
    #----------------------------------------------------------------------
        """
        handle persistence for WeatherStation object

        :param pObj: PersistenceObject object
        """

        self.pObj = pObj
        self.updstn = pObj.GetWindow()
        TLWHandler.__init__(self,pObj)


    #----------------------------------------------------------------------
    def GetKind(self):
    #----------------------------------------------------------------------
        """
        UpdateStn
        """

        return 'UpdateStn'

    #----------------------------------------------------------------------
    def Save(self):
    #----------------------------------------------------------------------
        """
        save UpdateStn's state
        """

        TLWHandler.Save(self)
        self.pObj.SaveValue('items',self.updstn.tc.getitems())

    #----------------------------------------------------------------------
    def Restore(self):
    #----------------------------------------------------------------------
        """
        restore UpdateStn's state
        """

        TLWHandler.Restore(self)
        items = self.pObj.RestoreValue('items')
        if items is not None:
            self.updstn.tc.setitems(items)

########################################################################
class UpdateStn(wx.Frame):
# cobbled from http://zetcode.com/wxpython/layout/
########################################################################
    """
    Form to update the station.  Form displays TextCntl to collect desired
    address stations should be near.  Once address is entered, map is populated
    and user can give choice of station.

    :param parent: parent object for this form
    :param wxstn: WeatherStation object, which holds current station
    :param tbicon: task bar (actually systray) icon object
    """

    BTN_OK = wx.NewId()
    BTN_CNCL = wx.NewId()
    LOGOBORDER = 20

    #----------------------------------------------------------------------
    def __init__(self,parent,wxstn,tbicon):
    #----------------------------------------------------------------------
        self.debug = False

        self.wxstn = wxstn
        self.tbicon = tbicon
        self.chosen = None

        self.formname = 'set station'
        wx.Frame.__init__(self, parent, wx.ID_ANY, self.formname)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_ICONIZE, self.onIconize)
        self.Bind(wx.EVT_MAXIMIZE, self.onMaximize)

        self.InitUI()
        self.Centre()
        self.Show()

        self.SetName(self.formname)
        self.pm = PersistenceManager()
        self.pm.Register(self,persistenceHandler=UpdateStnHandler)
        check = self.pm.Restore(self)
        if self.debug: print ('Position at UpdateStn.__init__ is {0}'.format(self.GetPosition()))

    #----------------------------------------------------------------------
    def InitUI(self):
    #----------------------------------------------------------------------
        """
        Initialize the form
        """
        self.panel = wx.Panel(self)

        font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        # hbox1 - address entry
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        st1 = wx.StaticText(self.panel, label='Enter address')
        st1.SetFont(font)
        hbox1.Add(st1, proportion=1, flag=wx.RIGHT, border=8)
        self.tc = wxextensions.AutoTextCtrl(self.panel,style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.onSearch, self.tc)
        hbox1.Add(self.tc, proportion=3, border=8)
        self.resultdisp = wx.StaticText(self.panel, label='')
        self.resultdisp.SetFont(font)
        hbox1.Add(self.resultdisp, proportion=1, border=8)
        self.vbox.Add(hbox1, flag=wx.EXPAND|wx.LEFT|wx.RIGHT|wx.TOP, border=10)

        self.vbox.Add((-1, 10))

        # hbox2 - station selection
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        st3 = wx.StaticText(self.panel, label='Select Station')
        st3.SetFont(font)
        hbox2.Add(st3, flag=wx.RIGHT, border=8)
        self.stnchoice = wx.Choice(self.panel,choices = [])             # self.stnchoice gets updated in onSearch()
        self.Bind(wx.EVT_CHOICE, self.EvtChoice, self.stnchoice)
        hbox2.Add(self.stnchoice)
        self.vbox.Add(hbox2, flag=wx.LEFT | wx.TOP, border=10)

        self.vbox.Add((-1, 10))

        # hbox3 - OK, Cancel buttons
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        # OK button
        b1 = wx.Button(self.panel, self.BTN_OK, "OK")
        self.Bind(wx.EVT_BUTTON, self.onOk, b1)
        b1.SetDefault()
        b1.SetSize(b1.GetBestSize())
        hbox3.Add(b1, border=8)
        # Cancel button
        b2 = wx.Button(self.panel, self.BTN_CNCL, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.onClose, b2)
        b2.SetSize(b2.GetBestSize())
        hbox3.Add(b2, border=8)
        self.vbox.Add(hbox3, flag=wx.LEFT|wx.RIGHT|wx.EXPAND, border=10)

        self.vbox.Add((-1, 10))

        # hbox4 - map
        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        bmp = wx.EmptyBitmap(400,400)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.Brush("black"))
        dc.SelectObject( wx.NullBitmap )
        self.mapimage = wx.StaticBitmap(self.panel,wx.ID_ANY,bmp)
        hbox4.Add(self.mapimage)
        self.vbox.Add(hbox4, flag=wx.CENTER, border=10)

        # hbox5 - logo
        self.logoimg = wulogo.GetImage()
        hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        panelwidth = 400.0  # based on width of hbox4
        scalefactor = (panelwidth-self.LOGOBORDER*2)/self.logoimg.Width
        scaledimg = self.logoimg.Scale(self.logoimg.Width*scalefactor, self.logoimg.Height*scalefactor, wx.IMAGE_QUALITY_HIGH)
        self.logo = wx.StaticBitmap(self.panel, bitmap=wx.BitmapFromImage(scaledimg))
        hbox5.Add(self.logo)
        self.vbox.Add(hbox5,flag=wx.ALL,border=self.LOGOBORDER)

        self.panel.SetSizerAndFit(self.vbox)
        self.Fit()

    #----------------------------------------------------------------------
    def onSearch(self, evt):
    #----------------------------------------------------------------------
        """
        Search for address, then display rest of frame
        """
        try:
            results = pygeocoder.Geocoder.geocode(self.tc.GetValue())
            self.tc.SetValue('')
        except:
            self.resultdisp.SetLabel('Address Not Found')
            self.tc.SetValue('')
            return
        if not results.valid_address:
            self.resultdisp.SetLabel('Invalid Address')
            return
        self.tc.additem(results.formatted_address)
        self.pm.Save(self)      # update persistence information
        self.resultdisp.SetLabel('')
        lat = results.coordinates[0]
        lon = results.coordinates[1]
        if wuaccess:        # set to False for fake address translation, to avoid use of apikey
            wu = urllib2.urlopen('http://api.wunderground.com/api/{0}/geolookup/q/{1},{2}.xml'.format(WUAPIKEY,lat,lon))
        else:
            if results.formatted_address[0:4] == '5575':
                wu = open('hollyhills.xml')
            else:
                wu = open('sandiego.xml')
        wuxml = wu.readlines()
        wu.close()

        # pull station data out of response
        # stations pulled are those <= MAXDISTANCE away from desired address, assuming MINSTATIONS have been selected
        # no more than MAXSTATIONS will be used
        MINSTATIONS = 3
        MAXSTATIONS = 10    # must be <= 26
        MAXDISTANCE = 10    # kilometers
        tree = ET.fromstringlist(wuxml)
        pws = tree.find('location').find('nearby_weather_stations').find('pws')
        stnlist_dec = []
        for stn in pws.findall('station'):
            stnd = {}
            stnd['string'] = ', '.join([l for l in[stn.find('neighborhood').text,stn.find('city').text,stn.find('state').text] if l is not None])    # skip empty text in any of these fields
            stnd['id'] = stn.find('id').text
            stnd['lat'] = float(stn.find('lat').text)
            stnd['lon'] = float(stn.find('lon').text)
            stnd['distkm'] = float(stn.find('distance_km').text)
            stnd['distmi'] = float(stn.find('distance_mi').text)
            stnlist_dec.append((stnd['distkm'],stnd))   # prepend distance for sorting
        stnlist_dec.sort()
        stnlist = [stn[1] for stn in stnlist_dec]   # remove decoration used for sorting
        labels = iter(string.ascii_uppercase[0:MAXSTATIONS])
        choices = []
        dmap = motionless.DecoratedMap()
        dmap.add_marker(motionless.LatLonMarker(float(lat),float(lon),size='tiny',color='green'))
        for stn in stnlist:
            try:
                label = next(labels)
            except StopIteration:
                break
            if stn['distkm'] > MAXDISTANCE and len(choices) > MINSTATIONS:
                break
            choice = '{0}: {1} ({2})'.format(label,stn['string'],stn['id'])
            dmap.add_marker(motionless.LatLonMarker(stn['lat'],stn['lon'],label=label))
            choices.append(choice)
        self.stnchoice.SetItems(choices)
        self.stnchoice.SetSize(self.stnchoice.GetBestSize())

        # prepare map image url
        mapurl = dmap.generate_url()
        maperror = False
        try:
            fp = urllib2.urlopen(mapurl)
            data = fp.read()
            fp.close()
            mapimg = wx.ImageFromStream(StringIO(data))
        except:
            self.resultdisp.SetLabel('Error processing map: {0}'.format(sys.exc_info()))
            maperror = True
            return

        # map
        if not maperror:
            bmp = mapimg.ConvertToBitmap()
            bmp.SetSize(bmp.GetSize())
            self.mapimage.SetBitmap(bmp)

        self.panel.SetSizerAndFit(self.vbox)
        self.Fit()

    #----------------------------------------------------------------------
    def onIconize(self, evt):
    #----------------------------------------------------------------------
        """
        Minimize to task bar
        """
        #self.onClose(evt)
        if self.debug: print ('Position at UpdateStn.onIconize is {0}'.format(self.GetPosition()))
        pass

    #----------------------------------------------------------------------
    def onMaximize(self, evt):
    #----------------------------------------------------------------------
        """
        Maximize
        """
        if self.debug: print ('Position at WxDisplay.onMaximize is {0}'.format(self.GetPosition()))
        pass

    #----------------------------------------------------------------------
    def EvtChoice(self, evt):
    #----------------------------------------------------------------------
        self.chosen = evt.GetString()

    #----------------------------------------------------------------------
    def onOk(self, evt):
    #----------------------------------------------------------------------
        """
        Update the station and close the window

        If nothing was chosen, no changes are made
        """
        if self.debug: print ('Position at UpdateStn.onClose is {0}'.format(self.GetPosition()))

        # get chosen station
        stnstring = self.chosen
        # stnstring = self.ch.getChoice()

        # None means no choice was made
        # else stnstring is of format 'City Name (stnid)'
        if stnstring is not None:
            for c in range(len(stnstring)-1,-1,-1):
                if stnstring[c] == '(':
                    start = c+1
                    break
            stnid = stnstring[start:-1]
            self.wxstn.setstation(stnid)
            self.tbicon.UpdateIcon('stnchange')

        self.pm.SaveAndUnregister(self)
        self.Destroy()

    #----------------------------------------------------------------------
    def onClose(self, evt):
    #----------------------------------------------------------------------
        """
        Just close the window without updating the station
        """
        if self.debug: print ('Position at UpdateStn.onCancel is {0}'.format(self.GetPosition()))
        self.pm.SaveAndUnregister(self)
        self.Destroy()


########################################################################
class MyIcon(wx.TaskBarIcon):
########################################################################
    TBMENU_OPEN = wx.NewId()
    TBMENU_SETSTN = wx.NewId()
    TBMENU_EXIT = wx.NewId()
    ID_ICON_TIMER = wx.NewId()

    #----------------------------------------------------------------------
    def __init__(self,frame,wxstn):
    #----------------------------------------------------------------------

        wx.TaskBarIcon.__init__(self)
        self.frame = frame
        self.wxstn = wxstn
        self.exiting = False        # flag to indicate we're trying to exit
        self.icon_timer = None      # prevent race condition

        # bind some events
        self.Bind(wx.EVT_MENU, self.OnMaximize, id=self.TBMENU_OPEN)
        self.Bind(wx.EVT_MENU, self.OnSetStn, id=self.TBMENU_SETSTN)
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_EXIT)
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnTaskBarLeftClick)
        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.OnTaskBarRightClick)

        # Set the image
        self.icon = IconText()
        currtemp = str(self.wxstn.gettemp())
        thisicon = self.icon.settext(currtemp)
        # self.SetIcon(thisicon,u'Current Temp = {0}\u00B0F'.format(currtemp))

        # initialize the form
        wxstring = self.wxstn.getwxstring()
        wxurl = self.wxstn.geturl()
        self.SetIcon(thisicon,wxstring)
        self.frame.settext(wxstring)
        self.frame.seturl(wxurl)
        self.frame.setlogoandfit()

    #----------------------------------------------------------------------
    def CreatePopupMenu(self, evt=None):
    #----------------------------------------------------------------------
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        menu = wx.Menu()
        menu.Append(self.TBMENU_OPEN, "Open")
        menu.Append(self.TBMENU_SETSTN, "Set Station")
        #menu.AppendSeparator()
        menu.Append(self.TBMENU_EXIT,   "Exit")
        return menu

    #----------------------------------------------------------------------
    def OnMaximize(self, evt):
    #----------------------------------------------------------------------
        """
        Request to maximize window
        """
        #self.frame = WxDisplay()
        self.frame.onMaximize(evt)

    #----------------------------------------------------------------------
    def OnSetStn(self, evt):
    #----------------------------------------------------------------------
        """
        Request to set a new active station
        """
        self.updatestn = UpdateStn(self.frame,self.wxstn,self)

    #----------------------------------------------------------------------
    def OnTaskBarClose(self, evt):
    #----------------------------------------------------------------------
        """
        Destroy the taskbar icon and frame from the taskbar icon itself
        """
        try:
            self.frame.shutdown()
            self.frame.Destroy()
        except:
            pass

        self.wxstn.shutdown()
        self.RemoveIcon()
        self.Destroy()
        self.exiting = True
        if self.icon_timer:
            self.icon_timer.Stop()

    #----------------------------------------------------------------------
    def OnTaskBarLeftClick(self, evt):
    #----------------------------------------------------------------------
        """
        handle left click.  toggle "Show" status
        """

        if not self.frame.IsShown():
            self.frame.onMaximize(evt)
        else:
            self.frame.onIconize(evt)

    #----------------------------------------------------------------------
    def OnTaskBarRightClick(self, evt):
    #----------------------------------------------------------------------
        """
        Create the right-click menu
        """

        menu = self.CreatePopupMenu()
        self.PopupMenu(menu)
        menu.Destroy()

    #----------------------------------------------------------------------
    def SetIconTimer(self):
    #----------------------------------------------------------------------
        """
        sets the icon timer
        """
        self.icon_timer = wx.Timer(self, self.ID_ICON_TIMER)
        wx.EVT_TIMER(self, self.ID_ICON_TIMER, self.UpdateIcon)
        if not self.exiting:
            self.icon_timer.Start(60*1000)    # query wunderground every minute

    #----------------------------------------------------------------------
    def UpdateIcon(self,event):
    #----------------------------------------------------------------------
        """
        periodic update of icon

        :param event: event which caused this method to be called
        """
        # don't bother if we're trying to exit
        if self.exiting: return

        # get current temp, update icon
        currtemp = str(self.wxstn.gettemp())
        thisicon = self.icon.settext(currtemp)

        # update form
        wxstring = self.wxstn.getwxstring()
        wxurl = self.wxstn.geturl()

        self.SetIcon(thisicon,wxstring) # TBD - need to abbreviate wxstring
        self.frame.settext(wxstring)
        self.frame.seturl(wxurl)
        self.frame.setlogoandfit()

#######################################################################
class MyApp(wx.App):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self,wundergroundstation):
    #----------------------------------------------------------------------
        """
        return MyApp object

        :param wxstn: WeatherStation object
        """
        wx.App.__init__(self, False)
        self.frame = WxDisplay()
        wxstn = WeatherStation(wundergroundstation)
        self.tbIcon = MyIcon(self.frame,wxstn)
        self.tbIcon.SetIconTimer()

################################################################################
def main():
################################################################################

    parser = argparse.ArgumentParser(version='{0} {1}'.format('weather',version.__version__))
    parser.add_argument('--nowuaccess',help='use option to inhibit wunderground access using apikey',action="store_true")
    args = parser.parse_args()
    global wuaccess
    wuaccess = not args.nowuaccess

    wundergroundstation = None

    # start the app
    app = MyApp(wundergroundstation)
    app.MainLoop()

# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

