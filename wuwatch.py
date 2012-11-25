#!/usr/bin/python
###########################################################################################
#   wuwatch - display weather underground data
#
#   Date		Author		Reason
#   ----		------		------
#   10/02/12	Lou King	Create
#   11/05/12    Lou King    Add window persistence
#   11/16/12    Lou King    Add set station form
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
import optparse
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
from wx.lib.agw.persist.persistencemanager import PersistenceManager
from wx.lib.agw.persist.persist_handlers import AbstractHandler,TLWHandler
import wx.lib.agw.hyperlink as hl

# home grown

# full weather string is in same order as this
DISPLAYFORMAT = ('' +
    'credit^{0},' +
    'location/full^{0},' +
    'station_id^Station ID: {0},' +
    'observation_time^{0},' +
    'temperature_string^Temperature: {0},' +
    'wind_string^Wind Speed: {0},' +
    'dewpoint_string^Dew Point: {0},' +
    'windchill_string^Wind Chill: {0},' +
    'pressure_string^Barometric Pressure: {0},' +
    'precip_1hr_string^Precipitation (current hour): {0},' +
    'precip_today_string^Precipitation (today): {0}'    # NOTE: no comma or + for last string
    )
DISPLAYKEYS = [f.split('^')[0] for f in DISPLAYFORMAT.split(',')]
DISPLAYFORMATS = [f.split('^')[1] for f in DISPLAYFORMAT.split(',')]
DISPLAYFIELDS = dict(zip(DISPLAYKEYS,DISPLAYFORMATS))

WUAPIKEY = '4290fe192dd34983'

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
class WeatherStation:
########################################################################
    #----------------------------------------------------------------------
    def __init__(self, station=None):
    #----------------------------------------------------------------------
        """
        return a WeatherStation object

        :param station: name of wunderground station, or None (default 'KMDIJAMS2')
        """
        if station is None:
            wundergroundstation = 'KMDIJAMS2'    # TODO: need to look in config file
        else:
            wundergroundstation = station
        self.setstation(wundergroundstation)

        self.debug = True

        self.wxstring = ''

    #----------------------------------------------------------------------
    def setstation(self,station):
    #----------------------------------------------------------------------
        """
        set the configured wunderground station

        :param station: name of wunderground station
        """
        self.wundergroundstation = station

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
            # pdb.set_trace()
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
        self.SetSizer(self.vbox)

        self.st = wx.StaticText(self.panel)
        self.vbox.Add(self.st,border=8)

        self.url = hl.HyperLinkCtrl(self.panel)
        self.Bind(hl.EVT_HYPERLINK_LEFT, self.onClick)
        self.vbox.Add(self.url)

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
        self.panel.SetSizerAndFit(self.vbox)
        self.Fit()

    #----------------------------------------------------------------------
    def seturl(self, url):
    #----------------------------------------------------------------------
        """
        set text for the form

        :param url: url to put into the form
        """

        self.url.SetURL(url)
        self.url.SetLabel('Current Observation')
        self.panel.SetSizerAndFit(self.vbox)
        self.Fit()

########################################################################
class StnChoice(wx.Panel):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self, parent):
    #----------------------------------------------------------------------
        wx.Panel.__init__(self, parent, wx.ID_ANY)

        wx.StaticText(self, wx.ID_ANY, "Select Station:", (15, 50), (75, -1))

        # TBD get possible stations from wunderground
        stations = {'KMDNEWMA2':'Lake Linganore','KMDIJAMS2':'Holly Hills, Ijamsville, MD'}
        stnchoices = ['{0} ({1})'.format(stations[stnid],stnid) for stnid in stations.keys()]

        self.ch = wx.Choice(self,wx.ID_ANY,(100, 50),choices = stnchoices)
        self.Bind(wx.EVT_CHOICE, self.EvtChoice, self.ch)
        self.chosen = None

    #----------------------------------------------------------------------
    def EvtChoice(self, event):
    #----------------------------------------------------------------------
        self.chosen = event.GetString()

    #----------------------------------------------------------------------
    def getChoice(self):
    #----------------------------------------------------------------------
        return self.chosen

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

    #----------------------------------------------------------------------
    def __init__(self,parent,wxstn,tbicon):
    #----------------------------------------------------------------------
        self.debug = False

        self.wxstn = wxstn
        self.tbicon = tbicon

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
        self.pm.Register(self,persistenceHandler=TLWHandler)
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
        hbox1.Add(st1, flag=wx.RIGHT, border=8)
        self.tc = wx.TextCtrl(self.panel,style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.onSearch, self.tc)
        hbox1.Add(self.tc, proportion=1, border=8)
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
        self.vbox.Add(hbox4, flag=wx.LEFT, border=10)

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
        self.resultdisp.SetLabel('')
        lat = results.coordinates[0]
        lon = results.coordinates[1]
        if False:        # set to False for fake address translation
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
        # self.updatestn = Example(self.frame,'Example')

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

        self.RemoveIcon()
        self.Destroy()

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
        self.icon_timer.Start(60*1000)    # query wunderground every minute

    #----------------------------------------------------------------------
    def UpdateIcon(self,event):
    #----------------------------------------------------------------------
        """
        periodic update of icon

        :param event: event which caused this method to be called
        """
        # get current temp, update icon
        currtemp = str(self.wxstn.gettemp())
        thisicon = self.icon.settext(currtemp)

        # update form
        wxstring = self.wxstn.getwxstring()
        wxurl = self.wxstn.geturl()

        self.SetIcon(thisicon,wxstring) # TBD - need to abbreviate wxstring
        self.frame.settext(wxstring)
        self.frame.seturl(wxurl)

#######################################################################
class MyApp(wx.App):
########################################################################

    #----------------------------------------------------------------------
    def __init__(self,wxstn):
    #----------------------------------------------------------------------
        """
        return MyApp object

        :param wxstn: WeatherStation object
        """
        wx.App.__init__(self, False)
        self.frame = WxDisplay()
        self.tbIcon = MyIcon(self.frame,wxstn)
        self.tbIcon.SetIconTimer()

################################################################################
def main():
################################################################################

    usage = "usage: %prog [options] [<wundergroundstation>]\n\n"
    usage += "where:\n"
    usage += "  <wundergroundstation>\toptional weather underground station"

    parser = optparse.OptionParser(usage=usage)
    (options, args) = parser.parse_args()

    wundergroundstation = None
    if len(args)>0:
        wundergroundstation = args.pop(0)

    stn = WeatherStation(wundergroundstation)

    # start the app
    app = MyApp(stn)
    app.MainLoop()

# ###############################################################################
# ###############################################################################
if __name__ == "__main__":
    main()

