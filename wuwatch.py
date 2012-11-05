#!/usr/bin/python
# ##########################################################################################
#	wuwatch - display weather underground data
#
#	Date		Author		Reason
#	----		------		------
#	10/02/12	Lou King	Create
#
# ##########################################################################################
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
#import Image, ImageDraw, ImageFont, ImageColor	# PIL

# github

# other
import wx

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
class MyForm(wx.Frame):
########################################################################
 
    #----------------------------------------------------------------------
    def __init__(self):
    #----------------------------------------------------------------------
        wx.Frame.__init__(self, None, wx.ID_ANY, "wunderground details", size=(350,200), 
            style=wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP|wx.FRAME_NO_TASKBAR)
        panel = wx.Panel(self)
        self.Bind(wx.EVT_CLOSE, self.onClose)
        self.Bind(wx.EVT_ICONIZE, self.onIconize)
        self.Bind(wx.EVT_MAXIMIZE, self.onMaximize)
        self.Show(False)    # start without showing form
        
        self.st = wx.StaticText(self) # static text widget
        
    #----------------------------------------------------------------------
    def onIconize(self, evt):
    #----------------------------------------------------------------------
        """
        Leave only the systray icon
        """
        #self.onClose(evt)
        self.Show(False)
 
    #----------------------------------------------------------------------
    def onMaximize(self, evt):
    #----------------------------------------------------------------------
        """
        Show the frame 
        """
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
        # self.st.Layout()
        # self.Layout()

########################################################################
class MyIcon(wx.TaskBarIcon):
########################################################################
    TBMENU_OPEN = wx.NewId()
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
        #menu.AppendSeparator()
        menu.Append(self.TBMENU_EXIT,   "Exit")
        return menu
 
    #----------------------------------------------------------------------
    def OnMaximize(self, evt):
    #----------------------------------------------------------------------
        """"""
        #self.frame = MyForm()
        self.frame.Show()
 
    #----------------------------------------------------------------------
    def OnTaskBarActivate(self, evt):
    #----------------------------------------------------------------------
        """"""
        pass
 
    #----------------------------------------------------------------------
    def OnTaskBarClose(self, evt):
    #----------------------------------------------------------------------
        """
        Destroy the taskbar icon and frame from the taskbar icon itself
        """
        try:
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
            self.frame.Show(True)
        else:
            self.frame.Show(False)
        
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
        self.SetIcon(thisicon,wxstring)
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
        self.frame = MyForm()
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

