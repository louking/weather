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

# pypi

# github

# other
import wx   # http://wxpython.org/download.php#stable
from wx.lib.agw.persist.persistencemanager import PersistenceManager
from wx.lib.agw.persist.persist_handlers import AbstractHandler,TLWHandler

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
        tree = ET.fromstringlist(wuxml) 
        wu.close()
        
        # pull out full weather string
        self.wxstring = ''
        fields = list(DISPLAYKEYS) # make a copy
        while len(fields) > 0:
            field = fields.pop(0)
            
            ###
            subfields = field.split('/')
            thisel = tree
            while len(subfields) > 0:
                subfield = subfields.pop(0)
                thisel = thisel.find(subfield)
            self.wxstring += DISPLAYFIELDS[field].format(thisel.text)
            ###
            # self.wxstring += DISPLAYFIELDS[field].format(tree.find(field).text)

            if len(fields) > 0:
                self.wxstring += '\n'
            
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
        self.formname = 'wunderground details'
        wx.Frame.__init__(self, None, wx.ID_ANY, self.formname, size=(350,200), 
            style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR)
        panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_ICONIZE, self.onIconize)
        self.Bind(wx.EVT_MAXIMIZE, self.onMaximize)
        
        self.debug = False

        self.st = wx.StaticText(self) # static text widget
        
        self.SetName(self.formname)
        self.pm = PersistenceManager()
        self.pm.Register(self,persistenceHandler=TLWHandler)
        check = self.pm.Restore(self)
        if self.debug: print ('Position at WxDisplay.__init__ is {0}'.format(self.GetPosition()))
        
        self.Show(False)    # start without showing form
        
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
        #self.Destroy()
        self.Show(False)
        
    #----------------------------------------------------------------------
    def settext(self, text):
    #----------------------------------------------------------------------
        """
        set text for the form
        
        :param text: text to put into the form
        """

        self.st.SetLabel(text)

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
########################################################################
 
    BTN_OK = wx.NewId()
    BTN_CNCL = wx.NewId()
    
    #----------------------------------------------------------------------
    def __init__(self,parent,wxstn,tbicon):
    #----------------------------------------------------------------------
        self.debug = False

        self.wxstn = wxstn
        self.tbicon = tbicon
        
        self.formname = 'update station'
        wx.Frame.__init__(self, parent, wx.ID_ANY, self.formname)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_ICONIZE, self.onIconize)
        self.Bind(wx.EVT_MAXIMIZE, self.onMaximize)
        
        # self.ch = StnChoice(self)
        wx.StaticText(self, wx.ID_ANY, "Select Station:", (15, 50), (75, -1))
        
        # TBD get possible stations from wunderground
        stations = {'KMDNEWMA2':'Lake Linganore','KMDIJAMS2':'Holly Hills, Ijamsville, MD'}
        stnchoices = ['{0} ({1})'.format(stations[stnid],stnid) for stnid in stations.keys()]
        
        ch = wx.Choice(self,wx.ID_ANY,(100, 50),choices = stnchoices)
        self.Bind(wx.EVT_CHOICE, self.EvtChoice, ch)
        self.chosen = None

        b = wx.Button(self, self.BTN_OK, "OK", (15, 80))
        self.Bind(wx.EVT_BUTTON, self.onOk, b)
        b.SetDefault()
        b.SetSize(b.GetBestSize())

        b = wx.Button(self, self.BTN_CNCL, "Cancel", (90, 80)) 
        self.Bind(wx.EVT_BUTTON, self.onClose, b)
        b.SetSize(b.GetBestSize())

        self.SetName(self.formname)
        self.pm = PersistenceManager()
        self.pm.Register(self,persistenceHandler=TLWHandler)
        check = self.pm.Restore(self)
        if self.debug: print ('Position at UpdateStn.__init__ is {0}'.format(self.GetPosition()))
        
        self.Show(True)    
        
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
        # save state first?  Need an OK button, I guess
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
        self.SetIcon(thisicon,wxstring)
        self.frame.settext(wxstring)

 
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
        # self.SetIcon(thisicon,u'Current Temp = {0}\u00B0F'.format(currtemp))
        self.SetIcon(thisicon,wxstring) # TBD - need to abbreviate wxstring
        self.frame.settext(wxstring)
        
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

