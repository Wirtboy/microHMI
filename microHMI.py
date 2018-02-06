###############################################################################
#                                                                             #
# microHMI - A light and reliable microcontroller HMI                         #
#                                                                             #
# Copyright (C) Hector Monzon, 2018. Under MIT license                        #
# http://www.opensource.org/licenses/mit-license.php                          #
#                                                                             #
# Version 1.0 by Hector Monzon and Eng Jose Barriola                          #
#                                                                             #
# Contact: hectorm0202@gmail.com                                              #
#                                                                             #
# Last edit by HM, 25/01/2018                                                 #
#                                                                             #
###############################################################################

######### To understand the widget structure please refer to the wtree.kv file

#################### Library imports
# Library for interaction with the operative system
import os
# I had to change the default audio provider because it was raising runtime
# errors. Default audio provider is gstplayer, any help is welcomed
os.environ['KIVY_AUDIO'] = 'sdl2'
#################### Kivy libraries import
# Library for previous configurations
from kivy.config import Config
# Configurations must be done before importing any other kivy libraries
# Disabling multitouch (remove if necessary)
Config.set("input", "mouse", "mouse,disable_multitouch")
# Disabling closing on ESC key
Config.set('kivy', 'exit_on_escape', '0')
# See Kivy documentation to understand the next imports
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.uix.slider import Slider
from kivy.uix.behaviors.compoundselection import CompoundSelectionBehavior
from kivy.uix.behaviors import FocusBehavior, DragBehavior
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.graphics import Color, Rectangle, Ellipse, Line
from kivy.uix.spinner import Spinner
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.properties import (ObjectProperty, ListProperty, StringProperty,
    NumericProperty, BooleanProperty)
from kivy.uix.tabbedpanel import TabbedPanel,TabbedPanelItem
from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.garden.graph import Graph, MeshLinePlot
#################### Database libraries, see sqlalchemy documentation
from sqlalchemy.orm import sessionmaker
from sqlalchemy import (create_engine, Column, Float, Integer, Numeric,
    String,Boolean, DateTime, ForeignKey, update)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,relationship,backref
#################### Python libraries, see each library documentation
from datetime import datetime
import time
import re
from pyfirmata import Arduino, util
import sys
from collections import OrderedDict
import webbrowser
from functools import partial
import serial
import glob

# Establishing the window's background color
Window.clearcolor = get_color_from_hex('#87FFFC')
# Setting up database, see sqlalchemy documentation
engine = create_engine('sqlite:///:memory:')
Session = sessionmaker(bind = engine)
session = Session()
Base = declarative_base()

class RTU(Base):
    __tablename__='remotes'

    RTU_id = Column(Integer,primary_key=True)
    RTU_name = Column(String(40))
    RTU_port = Column(String(40))
    #RTU_type = Column(String(40))

    DP=relationship('Dpoint',backref = 'rem1')
    AP=relationship('Apoint',backref = 'rem2')
    PP=relationship('Ppoint',backref = 'rem3')

class Dpoint(Base):
    __tablename__ = 'digipoints'

    DP_id = Column(Integer,primary_key=True)
    DP_tag = Column(String(40))
    DP_descrip = Column(String(200))
    DP_pinno = Column(Integer)
    DP_pinmo = Column(String(40))
    DP_alarmer = Column(Boolean)
    DP_RTUid = Column(Integer,ForeignKey('remotes.RTU_id'))

    DP = relationship('Pread', backref = 'Rdp')
    DAl = relationship('Alarm', backref = 'dal')

class Ppoint(Base):
    __tablename__ = 'pwmpoints'

    PP_id = Column(Integer,primary_key = True)
    PP_tag = Column(String(40))
    PP_descrip = Column(String(200))
    PP_pinno = Column(Integer)
    PP_max = Column(Float(2))
    PP_min = Column(Float(2))
    PP_pinmo = Column(Integer)
    PP_RTUid = Column(Integer(),ForeignKey('remotes.RTU_id'))
    PP_unit = Column(String(20))

    PP = relationship('Pread', backref = 'Rpp')

class Apoint(Base):
    __tablename__ = 'anapoints'

    AP_id = Column(Integer,primary_key = True)
    AP_tag = Column(String(40))
    AP_descrip = Column(String(200))
    AP_chilimit = Column(Numeric(12,2))
    AP_hilimit = Column(Numeric(12,2))
    AP_lowlimit = Column(Numeric(12,2))
    AP_clowlimit = Column(Numeric(12,2))
    AP_pinno = Column(Integer)
    AP_pinmo = Column(String(40))
    AP_RTUid = Column(Integer(),ForeignKey('remotes.RTU_id'))
    AP_graph = Column(Boolean)
    AP_unit = Column(String(20))

    AP = relationship('Pread', backref = 'Rap')
    AAl = relationship('Alarm', backref = 'aal')

class Alarm(Base):
    __tablename__ = 'alarmas'

    AL_id = Column(Integer, primary_key = True)
    AL_pnt = Column(String(30))
    AL_typ = Column(String(5))
    AL_time = Column(String(20))
    AL_value = Column(Integer())
    AL_apoint = Column(Integer(), ForeignKey('anapoints.AP_id'))
    AL_dpoint = Column(Integer(), ForeignKey('digipoints.DP_id'))

class Pread(Base):
    __tablename__ = 'lecturas'

    PR_id = Column(Integer, primary_key = True)
    PR_val = Column(Integer)
    PR_time = Column(String(20))
    PR_typ = Column(String(2))
    PR_apointid = Column(Integer(), ForeignKey('anapoints.AP_id'))
    PR_dpointid = Column(Integer(), ForeignKey('digipoints.DP_id'))
    PR_ppointid = Column(Integer(), ForeignKey('pwmpoints.PP_id'))

RTU.__table__.drop(engine, True)
Dpoint.__table__.drop(engine,True)
Apoint.__table__.drop(engine,True)
Ppoint.__table__.drop(engine, True)
Alarm.__table__.drop(engine, True)
Pread.__table__.drop(engine, True)

Base.metadata.create_all(engine)

####################   Kivy classes definition

########### Presentation screen

class Prescreen(Screen):
    hab = BooleanProperty(True)

    # init override to load the sounds necessary to the program on startup
    # Must be scheduled after a wait time or the program crashes
    def __init__(self, **kwargs):
        Clock.schedule_once(self.loadst, 2)
        super(Prescreen, self).__init__(**kwargs)

    # Sound-loading method and start button habilitation
    def loadst(self, *args):
        self.manager.get_screen('ihmsc').ids.ihm.tone1 = SoundLoader.load(os.getcwd() + '/sounds/barbeep.mp3')
        self.manager.get_screen('ihmsc').ids.ihm.tone2 = SoundLoader.load(os.getcwd() + '/sounds/blkbeep.mp3')
        self.manager.get_screen('ihmsc').ids.ihm.tone3 = SoundLoader.load(os.getcwd() + '/sounds/dbarbeep.mp3')
        self.hab = True

    # This method activates the start button action (screen transition)
    def chsc(self, txt, *args):
        if txt == 'Start':
            self.manager.current = 'dbsc'
        else: pass

# Hyperlink to the MIT license info
class Hyper(Label):

    # Click override to open the page on the link
    def on_touch_down(self, touch):
        if self.collide_point(touch.x, touch.y):
            webbrowser.open(self.text)

########### Database screen
# The screen itself controls including, loading and exporting a database
class DBScreen(Screen):
    # Property that holds the RTUs present in the screen's list
    myrtus = ObjectProperty()

    # Init override to declare myrtus as a dict
    def __init__(self, **kwargs):
        self.myrtus = {}
        super(DBScreen,self).__init__(**kwargs)

    # Method for opening the new remote configuration popup
    def pop(self, *args):
        newrpop = RTUPopup(caller = self, size = (800, 600))
        newrpop.open()

    # Method for loading a database from .txt file
    def loaddb(self):
        chfile = Chpop(caller = self)
        chfile.open()

    # Method for exporting a database to a .txt file
    def svpop(self, *args):
        if len(self.myrtus.keys()) == 0:
            hey = Tempop(title = 'Empty database')
            hey.ids['yo'].text = 'Nothing to export'
            hey.open()
        elif self.ids['RTUlst'].sel == None:
            hey = Tempop(title = 'Error')
            hey.ids['yo'].text = 'Select a remote'
            hey.open()
        else:
            sv = Savepop(caller = self)
            sv.open()

    # Method that builds the exported .txt file
    def export(self, txt, *args):
        q = session.query(RTU).filter(RTU.RTU_name == self.ids['RTUlst'].sel.text).all()
        dgs = session.query(Dpoint).filter(Dpoint.DP_RTUid == q.RTU_id).all()
        ants = session.query(Apoint).filter(Apoint.AP_RTUid == q.RTU_id).all()
        pps = session.query(Ppoint).filter(Ppoint.PP_RTUid == q.RTU_id).all()
        if not txt.endswith('.txt'):
            txt = txt + '.txt'
        if os.path.isfile(os.getcwd() + '\Reports\\' + txt):
            nope = Tempop(title = 'Error')
            nope.ids['yo'].text = 'Duplicated file name'
            nope.open()
        else:
            fl = open(os.getcwd() + '\Reports\\' + txt, 'w+')
            fl.write('RTU: ' + q.RTU_name + '\r\n')
            ds = 'Dpoints: '
            ans = 'Apoints: '
            ps = 'Ppoints: '
            for dg in dgs:
                ds = ds + dg.DP_pinmo + ', ' + dg.DP_tag + ', ' + ('S' if dg.DP_alarmer else 'N') + ', ' + dg.DP_descrip + ', ' + str(dg.DP_pinno)  + '; '
            for an in ants:
                ans = (ans + an.AP_tag + ', ' + an.AP_descrip + ', ' + str(an.AP_clowlimit).strip('.')[0] + ', ' + str(an.AP_lowlimit).strip('.')[0] + ', ' + str(an.AP_hilimit).strip('.')[0]
                    + ', ' + str(an.AP_chilimit).strip('.')[0] + ', ' + an.AP_unit + ',' + str(an.AP_pinno) + ', ' + ('S' if an.AP_graph else 'N') + '; ')
            for p in pps:
                ps = ps + p.PP_tag + ', ' + p.PP_descrip + ', ' + str(p.PP_max).strip('.')[0] + ', ' + str(p.PP_min).strip('.')[0] + ', ' + p.PP_unit + ',' + str(p.PP_pinno) + '; '
            ds = ds.rstrip('; ')
            ans = ans.rstrip('; ')
            ps = ps.rstrip('; ')
            fl.write('\n' + ds + '\r\n' + '\n' + ans + '\r\n' + '\n' + ps)
            fl.close()
            ok = Tempop(title = 'Success')
            ok.ids['yo'].text = 'Remote exported'
            ok.open()

# Popup to name files (exports and reports)
class Savepop(Popup):
    # This property identifies the class of the object that calls the popup
    caller = ObjectProperty()
    # If true this property establishes that the popup is for readings report
    preporter = BooleanProperty(False)
    # If true this property establishes that the popup is for alarms report
    areporter = BooleanProperty(False)

# This popup is using for loading files from the system (importing .txt or
# loading images)
class Chpop(Popup):
    # Contains the object that calls the popup
    caller = ObjectProperty()
    # Indicates if the popup is used to load an image
    imager = BooleanProperty(False)

    # Loads the .txt file imported and fills the RTUPopup
    def load(self, pt, filename,*args):
        txt = open(os.path.join(pt, filename[0]))
        rs = []
        ds = []
        ans = []
        ps = []
        fillpop = RTUPopup(caller = self.caller, size = (800,600))
        for line in txt:
            if line.startswith('RTUs'):
                ls = line.split(':')
                rs.append(ls[1].strip())
            if line.startswith('Dpoints'):
                ls = line.split(':')
                ds.append(ls[1].strip())
            elif line.startswith('Apoints'):
                ls = line.split(':')
                ans.append(ls[1].strip())
            elif line.startswith('Ppoints'):
                ls = line.split(':')
                ps.append(ls[1].strip())
        rs = rs[0].split(';')
        for r in rs:
            dbrem = RTU(
                    RTU_name=r.strip()
                    )
            session.add(dbrem)
            fillpop.nm = r.strip()
            fillpop.ids['rname'].text = r.strip()
        ds = ds[0].split(';')
        if ds != []:
            dno = 1
        else:
            dno = 0
        q = session.query(RTU).filter(RTU.RTU_name==r).first()
        for d in ds:
            d = d.split(',')
            newdp = Dpoint(
                    DP_pinmo = d[0].strip(),
                    DP_tag = d[1].strip(),
                    DP_alarmer = (True if d[2].strip() == 'S' else False),
                    DP_descrip = d[3].strip(),
                    DP_pinno = int(d[4].strip())
                    )
            newdp.rem1 = q
            session.add(newdp)
            if dno == 1:
                fillpop.ids['digi1'].ids['tag'].text = d[1].strip()
                fillpop.ids['digi1'].ids['descrip'].text = d[3].strip()
                fillpop.ids['digi1'].ids['pin'].text = d[4].strip()
                fillpop.ids['digi1'].ids['pinmode'].text = d[0].strip()
                if d[2].strip() == 'S':
                    fillpop.ids['digi1'].ids['norstat'].active = True
                else:
                    fillpop.ids['digi1'].ids['norstat'].active = False
                dno += 1
            elif dno > 1:
                fillpop.ids['digi1'].autofill(d)
        ans = ans[0].split(';')
        if ans != []:
            ano = 1
        else:
            ano = 0
        for an in ans:
            an = an.split(',')
            newap = Apoint(
                        AP_tag = an[0].strip(),
                        AP_descrip = an[1].strip(),
                        AP_clowlimit = float(an[2].strip()),
                        AP_lowlimit = float(an[3].strip()),
                        AP_hilimit = float(an[4].strip()),
                        AP_chilimit = float(an[5].strip()),
                        AP_unit = an[6].strip(),
                        AP_pinno = int(an[7].strip()),
                        AP_pinmo = 'I',
                        AP_graph = (True if an[8].strip() == 'S' else False)
                        )
            newap.rem2 = q
            session.add(newap)
            if ano == 1:
                fillpop.ids['ana1'].ids['tag'].text = an[0].strip()
                fillpop.ids['ana1'].ids['descrip'].text = an[1].strip()
                fillpop.ids['ana1'].ids['LL'].text = an[2].strip()
                fillpop.ids['ana1'].ids['L'].text = an[3].strip()
                fillpop.ids['ana1'].ids['H'].text = an[4].strip()
                fillpop.ids['ana1'].ids['HH'].text = an[5].strip()
                fillpop.ids['ana1'].ids['unit'].text = an[6].strip()
                fillpop.ids['ana1'].ids['pin'].text = an[7].strip()
                if an[8].strip() == 'S':
                    fillpop.ids['ana1'].ids['gr'].active = True
                else:
                    fillpop.ids['ana1'].ids['gr'].active = False
                ano += 1
            elif ano > 1:
                fillpop.ids['ana1'].autofill(an)
        ps = ps[0].split(';')
        if ps != []:
            pno = 1
        else:
            pno = 0
        for p in ps:
            p = p.split(',')
            newpp = Ppoint(
                    PP_tag = p[0].strip(),
                    PP_descrip = p[1].strip(),
                    PP_max = int(p[2].strip()),
                    PP_min = int(p[3].strip()),
                    PP_unit = p[4].strip(),
                    PP_pinno = int(p[5].strip()),
                    PP_pinmo= 'P'
                    )
            newpp.rem3=q
            session.add(newpp)
            if pno == 1:
                fillpop.ids['p1'].ids['tag'].text = p[0].strip()
                fillpop.ids['p1'].ids['descrip'].text = p[1].strip()
                fillpop.ids['p1'].ids['maxi'].text = p[2].strip()
                fillpop.ids['p1'].ids['mini'].text = p[3].strip()
                fillpop.ids['p1'].ids['unit'].text = p[4].strip()
                fillpop.ids['p1'].ids['pin'].text = p[5].strip()
                pno += 1
            elif pno > 1:
                fillpop.ids['p1'].autofill(p)
        ok = Tempop(title = 'Success')
        ok.ids['yo'].text = 'Remote loaded'
        ok.open()
        fillpop.comrtu()

# Remote configuration popup
class RTUPopup(Popup):
    caller = ObjectProperty()
    # Name of the remote linked to the popup
    nm = StringProperty()
    # Digital tabs on the popup
    dtabsno = NumericProperty(1)
    # Analogic tabs on the popup
    atabsno = NumericProperty(1)
    # Ptabs on the popup
    ptabsno = NumericProperty(1)

    # Method that adds the remote to the list
    def comrtu(self,*args):
        self.nm = self.ids['rname'].text
        if self.nm == '':
            hey = Tempop(title = 'Error')
            hey.ids['yo'].text = 'Indicate remote name'
            hey.open()
        else:
            self.caller.ids['RTUlst'].add_elm(self.nm)
            session.commit()
            self.caller.myrtus[self.nm] = self

    # Methos that cancels changes made to the DB
    def rollrtu(self,*args):
        session.rollback()

# The next three classes are the tabs that a RTUpopup holds. Same name
# properties on them fulfill the same purposes
class Digitab(TabbedPanelItem):
    # Local register of point id linked to the tab
    dps = ListProperty()
    # Name of the remote
    rnamem = StringProperty()
    # Point object linked to the tab for establishing the backref (see
    # SQLAlchemy)
    pnt = ObjectProperty()

    # Validates the data input on the tab
    def savedp(self,tag,stat,desc,pinno,pinmo,*args):
        self.rnamem = self.parent.parent.parent.parent.parent.parent.parent.parent.parent.ids['rname'].text
        if self.rnamem == '':
            hey = Tempop(title = 'Not saved')
            hey.ids['yo'].text = 'Indicate remote name'
            hey.open()
        elif tag == '' or pinno == '':
            hey = Tempop(title = 'Not saved')
            hey.ids['yo'].text = 'Critical field empty'
            hey.open()
        elif self.id in self.dps:
            pass
        else:
            self.dps.append(self.id)
            q = session.query(RTU).filter(RTU.RTU_name == self.rnamem).first()
            if q == None:
                newr = RTU(RTU_name = self.rnamem)
                session.add(newr)
                q = session.query(RTU).filter(RTU.RTU_name == self.rnamem).first()
            newdp = Dpoint(
                        DP_tag = tag,
                        DP_descrip = desc,
                        DP_alarmer = stat,
                        DP_pinno = int(pinno),
                        DP_pinmo = pinmo
                        )
            newdp.rem1 = q
            session.add(newdp)
            self.pnt = newdp
            hey = Tempop(title = tag)
            hey.open()

    # Adds a new tab
    def newtab(self,nm):
        newdtab = Digitab(rnamem = nm)
        self.parent.parent.parent.parent.add_widget(newdtab)
        self.parent.parent.parent.parent.switch_to(newdtab)
        self.parent.parent.parent.parent.parent.parent.parent.parent.parent.dtabsno += 1

    # Autofills the tab if the DB is imported
    def autofill(self, dp):
        newdtab = Digitab()
        newdtab.ids['tag'].text = dp[1].strip()
        newdtab.ids['descrip'].text = dp[3].strip()
        newdtab.ids['pin'].text = dp[4].strip()
        newdtab.ids['pinmode'].text = dp[0].strip()
        if dp[2].strip() == 'S':
            newdtab.ids['norstat'].active = True
        else:
            newdtab.ids['norstat'].active = False
        self.parent.add_widget(newdtab)

    # Erases the tab and its linked point
    def erasept(self):
        if self.parent.parent.parent.parent.parent.parent.parent.parent.parent.dtabsno == 1:
            nope = Tempop(title = 'Error')
            nope.ids['yo'].text = 'Cannot erase only tab'
            nope.open()
        else:
            self.parent.parent.parent.parent.parent.parent.parent.parent.parent.dtabsno += -1
            for tab in reversed(self.parent.parent.parent.parent.tab_list):
                if tab == self:
                    pass
                else:
                    self.parent.parent.parent.parent.switch_to(tab)
                    break
            self.parent.remove_widget(self)
            if self.id in self.dps:
                self.dps.pop(int(self.dps.index(self.id)))
                session.delete(self.pnt)
                q = session.query(Dpoint).all()

class Anatab(TabbedPanelItem):
    rnamem = StringProperty()
    # Same as dps in digitab
    aps = ListProperty()
    pnt = ObjectProperty()

    # Same as savedp in digitab
    def saveap(self,tag,desc,L,LL,H,HH,pinno,pinmo,gr,unit,*args):
        self.rnamem = self.parent.parent.parent.parent.parent.parent.parent.parent.parent.ids['rname'].text
        if self.rnamem == '':
            hey = Tempop(title = 'Not saved')
            hey.ids['yo'].text = 'Indicate remote name'
            hey.open()
        elif self.id in self.aps:
            pass
        elif tag == '' or L == '' or LL == '' or H == '' or HH == '' or pinno == '':
            hey = Tempop(title = 'Not saved')
            hey.ids['yo'].text = 'Critical field empty'
            hey.open()
        else:
            self.aps.append(self.id)
            q = session.query(RTU).filter(RTU.RTU_name == self.rnamem).first()
            if q == None:
                newr = RTU(RTU_name = self.rnamem)
                session.add(newr)
                q = session.query(RTU).filter(RTU.RTU_name == self.rnamem).first()
            newap = Apoint(
                        AP_tag = tag,
                        AP_descrip = desc,
                        AP_lowlimit = float(L),
                        AP_clowlimit = float(LL),
                        AP_hilimit = float(H),
                        AP_chilimit = float(HH),
                        AP_pinno = int(pinno),
                        AP_pinmo = pinmo,
                        AP_graph = gr,
                        AP_unit = unit
                        )
            newap.rem2 = q
            session.add(newap)
            self.pnt = newap
            hey = Tempop(title = tag)
            hey.open()

    def newtab(self,nm):
        newdtab = Anatab(rnamem = nm)
        self.parent.parent.parent.parent.add_widget(newdtab)
        self.parent.parent.parent.parent.switch_to(newdtab)
        self.parent.parent.parent.parent.parent.parent.parent.parent.parent.atabsno += 1

    def autofill(self, an):
        newatab = Anatab()
        newatab.ids['tag'].text = an[0].strip()
        newatab.ids['descrip'].text = an[1].strip()
        newatab.ids['LL'].text = an[2].strip()
        newatab.ids['L'].text = an[3].strip()
        newatab.ids['H'].text = an[4].strip()
        newatab.ids['HH'].text = an[5].strip()
        newatab.ids['unit'].text = an[6].strip()
        newatab.ids['pin'].text = an[7].strip()
        if an[8].strip() == 'S':
            newatab.ids['gr'].active = True
        else:
            newatab.ids['gr'].active = False
        self.parent.add_widget(newatab)

    # Method to change between a input anatab and an output anatab (Ptab)
    def chtab(self, nm):
        ptab = Ptab(rnamem = nm)
        if self.id not in self.aps:
            self.parent.parent.parent.parent.add_widget(ptab)
            self.parent.parent.parent.parent.switch_to(ptab)
            self.parent.parent.parent.parent.remove_widget(self)
        else:
            self.parent.parent.parent.parent.add_widget(ptab)
            self.parent.parent.parent.parent.switch_to(ptab)

    def erasept(self):
        if self.parent.parent.parent.parent.parent.parent.parent.parent.parent.atabsno == 1:
            nope = Tempop(title = 'Error')
            nope.ids['yo'].text = 'Cannot erase only tab'
            nope.open()
        else:
            self.parent.parent.parent.parent.parent.parent.parent.parent.parent.atabsno += -1
            for tab in reversed(self.parent.parent.parent.parent.tab_list):
                if tab == self:
                    pass
                else:
                    self.parent.parent.parent.parent.switch_to(tab)
                    break
            self.parent.remove_widget(self)
            if self.id in self.aps:
                self.aps.pop(int(self.aps.index(self.id)))
                session.delete(self.pnt)

class Ptab(TabbedPanelItem):
    rnamem = StringProperty()
    # Same as aps y dps
    ps = ListProperty()
    pnt = ObjectProperty()

    def savepp(self,tag,desc,pinno,pinmo,maxi,mini,unit,*args):
        self.rnamem = self.parent.parent.parent.parent.parent.parent.parent.parent.parent.ids['rname'].text
        if self.rnamem == '':
            hey = Tempop(title = 'Not saved')
            hey.ids['yo'].text = 'Indicate remote name'
            hey.open()
        elif self.id in self.ps:
            pass
        elif tag == '' or maxi == '' or mini == '' or pinno == '':
            hey = Tempop(title = 'Not saved')
            hey.ids['yo'].text = 'Critical field empty'
            hey.open()
        else:
            q = session.query(RTU).filter(RTU.RTU_name == self.rnamem).first()
            self.ps.append(self.id)
            if q == None:
                newr = RTU(RTU_name = self.rnamem)
                session.add(newr)
                q = session.query(RTU).filter(RTU.RTU_name == self.rnamem).first()
            newpp = Ppoint(
                        PP_tag = tag,
                        PP_descrip = desc,
                        PP_pinno = int(pinno),
                        PP_pinmo = pinmo,
                        PP_max = int(maxi),
                        PP_min = int(mini),
                        PP_unit = unit
                        )
            newpp.rem3 = q
            session.add(newpp)
            self.pnt = newpp
            hey = Tempop(title = tag)
            hey.open()

    def newtab(self,nm):
        newdtab = Ptab(rnamem = nm)
        self.parent.parent.parent.parent.add_widget(newdtab)
        self.parent.parent.parent.parent.switch_to(newdtab)
        self.parent.parent.parent.parent.parent.parent.parent.parent.parent.ptabsno += 1

    def autofill(self, p):
        newptab = Ptab()
        newptab.ids['tag'].text = p[0].strip()
        newptab.ids['descrip'].text = p[1].strip()
        newptab.ids['maxi'].text = p[2].strip()
        newptab.ids['mini'].text = p[3].strip()
        newptab.ids['unit'].text = p[4].strip()
        newptab.ids['pin'].text = p[5].strip()
        self.parent.add_widget(newptab)

    # Changes Ptab to Anatab
    def chtab(self, nm):
        atab= Anatab(rnamem = nm)
        if self.id not in self.ps:
            self.parent.parent.parent.parent.add_widget(atab)
            self.parent.parent.parent.parent.switch_to(atab)
            self.parent.parent.parent.parent.remove_widget(self)
        else:
            self.parent.parent.parent.parent.add_widget(atab)
            self.parent.parent.parent.parent.switch_to(atab)

    def erasept(self):
        if self.parent.parent.parent.parent.parent.parent.parent.parent.parent.ptabsno == 1:
            nope = Tempop(title = 'Error')
            nope.ids['yo'].text = 'Cannot erase only tab'
            nope.open()
        else:
            self.parent.parent.parent.parent.parent.parent.parent.parent.parent.ptabsno += -1
            for tab in reversed(self.parent.parent.parent.parent.tab_list):
                if tab == self:
                    pass
                else:
                    self.parent.parent.parent.parent.switch_to(tab)
                    break
            self.parent.remove_widget(self)
            if self.id in self.ps:
                self.ps.pop(int(self.ps.index(self.id)))
                session.delete(self.pnt)
                q = session.query(Ppoint).all()

# Selectable list of current remotes
class Lista(FocusBehavior, CompoundSelectionBehavior, GridLayout):
    # Current remotes on list
    RTUs = ListProperty()
    # Currently selected remote
    sel = ObjectProperty()
    # Indicates if the list holds remotes or alarms
    rtulst = BooleanProperty()

    # Keyboard interactions control
    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if super(Lista, self).keyboard_on_key_down(
            window, keycode, text, modifiers):
            return True
        if self.select_with_key_down(window, keycode, text, modifiers):
            return True
        return False

    def keyboard_on_key_up(self, window, keycode):
        if super(Lista, self).keyboard_on_key_up(window, keycode):
            return True
        if self.select_with_key_up(window, keycode):
            return True
        return False

    # Override of the label creation method to link label_touch_down and
    # label_touch_up to their touch events (see below)
    def add_widget(self, widget):
        widget.bind(on_touch_down = self.label_touch_down,
                    on_touch_up = self.label_touch_up)
        return super(Lista, self).add_widget(widget)

    # Method that handles click and double click events
    def label_touch_down(self, label, touch):
        if label.collide_point(*touch.pos):
            self.select_with_touch(label, touch)
        if touch.is_double_tap and label.collide_point(*touch.pos) and self.rtulst:
            self.parent.parent.parent.myrtus[label.text].open()

    # Method that de-selects list objects on off-object click
    def label_touch_up(self, label, touch):
        if not (label.collide_point(*touch.pos) or
                self.touch_multiselect):
            self.deselect_node(label)

    # Method that selects an object and draws the gray selection box
    def select_node(self, node):
        with node.canvas.before:
            Color(*(0,0,0,0.5))
            Rectangle(pos=node.pos, size=node.size)
        self.sel = node
        return super(Lista, self).select_node(node)

    # Method that handles de-selection and erases the selection box
    def deselect_node(self, node):
        with node.canvas.before:
            Color(*(get_color_from_hex('#87FFFC')))
            Rectangle(pos=node.pos,size= node.size)
        super(Lista, self).deselect_node(node)

    # Method for adding new elements to the list
    def add_elm(self, name, *args):
        if name not in self.RTUs:
            self.RTUs.append(name)
            newRTU = Label(text = '{0}'.format(name), size_hint_y = None, height = 40, color = (0,0,0,1))
            self.add_widget(newRTU)
        else:
            pass

    # Method for erasing a selected list element
    def erase(self, node):
        self.remove_widget(node)
        q = session.query(RTU).filter(RTU.RTU_name == node.text).first()
        ds = session.query(Dpoint).filter(Dpoint.DP_RTUid == q.RTU_id).all()
        ans = session.query(Apoint).filter(Apoint.AP_RTUid == q.RTU_id).all()
        ps = session.query(Ppoint).filter(Ppoint.PP_RTUid == q.RTU_id).all()
        print q
        session.delete(q)
        for d in ds:
            print d
            session.delete(d)
        for an in ans:
            print an
            session.delete(an)
        for p in ps:
            print p
            session.delete(p)
        self.RTUs.pop(self.RTUs.index(node.text))

# Toggle button to indicate a point mode (Input-Output)
class Select(Button):
    # Override of the click event handler to change the text on the button
    def on_touch_down(self,touch):
        if self.collide_point(*touch.pos):
            if self.text == 'IN':
                self.text = 'OUT'
            elif self.text == 'OUT':
                self.text = 'IN'
        super(Select, self).on_touch_down(touch)

# Multipurpose temporal notification popups
class Tempop(Popup):
    # Override of the init for the popup to disappear after a second
    def __init__(self, **kwargs):
        super(Tempop, self).__init__(**kwargs)
        Clock.schedule_once(self.dismiss, 1)

# Number-only text input for pin numbers and limits
class FloatInput(TextInput):
    # Regular expressions filter pattern
    pat = re.compile('[^0-9]')

    # Input filter method
    def insert_text(self, substring, from_undo=False):
        pat = self.pat
        if '.' in self.text:
            s = re.sub(pat, '', substring)
        else:
            s = '.'.join([re.sub(pat, '', s) for s in substring.split('.', 1)])
        return super(FloatInput, self).insert_text(s, from_undo=from_undo)

# Checkbox that can only be active the point linked to its tab is on
# input mode (only input points require alarms)
class Cheeky(CheckBox):
    # Holds the point mode
    mode = StringProperty()

    # Override of the click event so it only changes if the mode is IN
    def on_touch_up(self,touch):
        super(Cheeky,self).on_touch_up(touch)
        if self.mode == 'OUT':
            self.active = False

############# HMI Screen
class HMIscreen(Screen):
    pass

# Popups to select widget subtypes: pumps, valves, tanks, etc.
class Selectpop(Popup):
    caller = ObjectProperty()
    # Modifies content of the popup according to type of the caller element
    typ = StringProperty()

# Port selection popup that appears when the start button is pressed
class Portpop(Popup):
    # Holds name of the remote connected
    myrem = StringProperty()
    caller = ObjectProperty()

    # Method detects if a remote is connected to a port
    def checkport(self, *args):
        if sys.platform.startswith('win'):
            ports = ['COM%s' % (i + 1) for i in range(256)]
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty"
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/tty.*')
        else:
            raise EnvironmentError('Unsupported platform')
        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        if result == []:
            pass
        else:
            self.ids['ptspin1'].values = result

    # Assigns the ports available to the spinner on the popup
    def assport(self, myrem, *args):
        q = session.query(RTU).filter(RTU.RTU_name == self.myrem).first()
        q.RTU_port = self.ids['ptspin1'].text
        session.commit()
        self.caller.caniscan(myrem)

### Next 5 classes are for display widgets. Each widget contains its type
### and an indicator that tells the program if the widget has been assigned
### to a database element. If it has, the widget also contains the information
### of its linked point.
### Same name properties and methods fulfill the same purposes

# Basic digital element (I/O)
class Blinker(DragBehavior,Widget):
    # Blinker current state
    stat = BooleanProperty()
    # linked point tag
    name = StringProperty()
    # linked point description
    desc = StringProperty()
    # Value of the state (1 or 0), for output widget control
    value = NumericProperty()
    # Pin mode (input or output)
    pinmo = StringProperty()
    # Pin object for the firmata protocol
    pin = ObjectProperty()
    # Indicates if widget should raise alarmas
    alarmer = BooleanProperty()
    # Indicates if widget is currently selected
    sel = BooleanProperty(False)
    # Indicates that element is selectable
    selectable = BooleanProperty(True)
    # Indicates if widget is linked
    ass = BooleanProperty(False)
    # Widget type (d - digital)
    ptyp = StringProperty('d')
    # Pin number
    pinno = StringProperty()

    # Method for changing the color of an input pin if state changes
    def measure(self):
        if self.pinmo=='IN':
            Clock.schedule_interval(partial(self.chcolor, False), 1)

    # Method that changes color and state of an output pin on click
    def chstat(self):
        if self.value==1:
            self.pin.write(0)
            self.value=0
        else:
            self.pin.write(1)
            self.value=1

    # Method that detects state changes to raise alarms if indicated
    def chcolor(self, fst, *args):
        if not fst:
            if self.stat != self.pin.read() and self.alarmer:
                self.parent.rise(self.name, self.value, 'd' , self.desc)
                if not self.parent.parent.manager.current == 'almsc':
                    if self.parent.tone2:
                        self.parent.tone2.play()
        if self.pin.read() == True:
            self.value = 0
            self.stat = self.pin.read()
        else:
            self.value = 1
            self.stat = self.pin.read()

    # Clock for scheduling state change detection
    def end(self,*args):
        Clock.unschedule(self.chcolor)

    # Click override. Changes state on output elements and opens the
    # linking popup if double click
    def on_touch_up(self,touch):
        super(Blinker, self).on_touch_up(touch)
        if self.collide_point(touch.x,touch.y):
            if self.pinmo == 'OUT' and self.parent.running:
                self.chstat()
            if touch.is_double_tap and not self.parent.running and not self.ass:
                q = session.query(RTU).first()
                if q == None:
                    hey = Tempop(title = 'Empty database')
                    hey.ids['yo'].text = 'Nothing to link'
                    hey.open()
                else:
                    rs = session.query(RTU).all()
                    DBpop = DBPopup(target_element = self, typ = 'd')
                    for r in rs:
                        dgs = session.query(Dpoint).filter(Dpoint.DP_RTUid==r.RTU_id).all()
                        DBpop.ids['ptspin1'].rvalues[r.RTU_name] = []
                        for dg in dgs:
                            if dg.DP_tag not in self.parent.asspts:
                                DBpop.ids['ptspin1'].rvalues[r.RTU_name].append(dg.DP_tag)
                        DBpop.ids['rspin'].values.append(r.RTU_name)
                    DBpop.open()

    # Restart of the widget's value
    def restart(self,*args):
        self.value=0

# Next two classes are bars (analogic input widgets)
class Ingage(DragBehavior,Widget):
    name = StringProperty()
    desc = StringProperty()
    value = NumericProperty()
    rem = ObjectProperty()
    pinmo = StringProperty()
    pin = ObjectProperty()
    # Value limits for raising alarms
    ch = NumericProperty()
    h = NumericProperty()
    l = NumericProperty()
    cl = NumericProperty()
    # If reading of the element is "None", a note will be displayed
    note = StringProperty()
    sel = BooleanProperty(False)
    selectable = BooleanProperty(True)
    # If true eleement's value will be plotted
    graphable = BooleanProperty(False)
    # List of values to plot
    plp = ListProperty()
    ass = BooleanProperty(False)
    # User establisehd units
    unit = StringProperty()
    # Indicates if the element is currently on alarm state
    alarming = BooleanProperty(False)
    ptyp = StringProperty('a')
    pinno = StringProperty()

    # Method that sets up the plotting area according to the number of plots
    def setgraph(self, *args):
        if self.graphable:
            if self.parent.parent.manager.get_screen('almsc').ids.pl1.text == 'Value 1':
                self.parent.parent.manager.get_screen('almsc').ids.pl1.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0,0,1,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[0])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10
            elif self.parent.parent.manager.get_screen('almsc').ids.pl2.text == 'Value 2':
                self.parent.parent.manager.get_screen('almsc').ids.pl2.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0.4,0.2,0.6,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[1])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10
            elif self.parent.parent.manager.get_screen('almsc').ids.pl3.text == 'Value 3':
                self.parent.parent.manager.get_screen('almsc').ids.pl3.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0.9,0.9,0.05,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[2])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10
            elif self.parent.parent.manager.get_screen('almsc').ids.pl4.text == 'Value 4':
                self.parent.parent.manager.get_screen('almsc').ids.pl4.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0.11,0.95,0.93,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[3])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10

    # Clock that schedules the method for bar animation
    def measure(self):
        Clock.schedule_interval(self.setbar, 1)

    # This method reads the element and adjust the bar animation. Also raises
    # alarms
    def setbar(self, *args):
        if self.pin.read()==None:
            self.value=0
        else:
            a = self.ch-self.cl
            self.value = (a*self.pin.read())+self.cl
        if self.graphable:
            self.plp.append(self.value)
            self.parent.uplot(self.name,self.plp)
        self.beep()

    # Compares read values to limits and indicates if an alarm should be raised
    def beep(self,*args):
        if self.value >= self.ch:
            self.alarming = True
            self.parent.rise(self.name,self.value,'HH',self.desc)
            if not self.parent.parent.manager.current == 'almsc':
                    if self.parent.tone3:
                            self.parent.tone3.play()
        elif self.value <= self.cl:
            self.alarming = True
            self.parent.rise(self.name,self.value,'LL',self.desc)
    	    if not self.parent.parent.manager.current == 'almsc':
                if self.parent.tone3:
                    self.parent.tone3.play()
        elif self.value < self.l and self.value > self.cl:
            self.alarming = True
            self.parent.rise(self.name,self.value,'L', self.desc)
            if not self.parent.parent.manager.current == 'almsc':
                if self.parent.tone1:
                    self.parent.tone1.play()
        elif self.value > self.h and self.value < self.ch:
            self.alarming = True
            self.parent.rise(self.name,self.value,'H',self.desc)
            if not self.parent.parent.manager.current == 'almsc':
                if self.parent.tone1:
                    self.parent.tone1.play()
        else:
            self.alarming = False

    # Stops element scan
    def end(self,*args):
        Clock.unschedule(self.setbar)

    # Open linking popup on double click
    def on_touch_up(self,touch):
        super(Ingage, self).on_touch_up(touch)
        if self.collide_point(touch.x,touch.y):
            if touch.is_double_tap and not self.parent.running and not self.ass:
                q = session.query(RTU).first()
                if q == None:
                    hey = Tempop(title = 'Empty database')
                    hey.ids['yo'].text = 'Nothing to link'
                    hey.open()
                else:
                    rs = session.query(RTU).all()
                    DBpop = DBPopup(target_element = self, typ = 'a')
                    for r in rs:
                        ans = session.query(Apoint).filter(Apoint.AP_RTUid==r.RTU_id).all()
                        DBpop.ids['ptspin1'].rvalues[r.RTU_name] = []
                        for an in ans:
                            if an.AP_tag not in self.parent.asspts:
                                DBpop.ids['ptspin1'].rvalues[r.RTU_name].append(an.AP_tag)
                        DBpop.ids['rspin'].values.append(r.RTU_name)
                    DBpop.open()

    def restart(self,*args):
        self.value=0

# Horizontal bar
class Ingageh(DragBehavior,Widget):
    name = StringProperty()
    desc = StringProperty()
    value = NumericProperty()
    rem = ObjectProperty()
    pinmo=StringProperty()
    pin=ObjectProperty()
    ch=NumericProperty()
    h=NumericProperty()
    l=NumericProperty()
    cl=NumericProperty()
    note=StringProperty()
    sel = BooleanProperty(False)
    selectable = BooleanProperty(True)
    graphable = BooleanProperty(False)
    plp = ListProperty()
    ass = BooleanProperty(False)
    unit = StringProperty()
    alarming = BooleanProperty(False)
    ptyp = StringProperty('a')
    pinno = StringProperty()

    def setgraph(self, *args):
        if self.graphable:
            if self.parent.parent.manager.get_screen('almsc').ids.pl1.text == 'Value 1':
                self.parent.parent.manager.get_screen('almsc').ids.pl1.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0,0,1,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[0])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10
            elif self.parent.parent.manager.get_screen('almsc').ids.pl2.text == 'Value 2':
                self.parent.parent.manager.get_screen('almsc').ids.pl2.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0.4,0.2,0.6,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[1])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10
            elif self.parent.parent.manager.get_screen('almsc').ids.pl3.text == 'Value 3':
                self.parent.parent.manager.get_screen('almsc').ids.pl3.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0.9,0.9,0.05,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[2])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10
            elif self.parent.parent.manager.get_screen('almsc').ids.pl4.text == 'Value 4':
                self.parent.parent.manager.get_screen('almsc').ids.pl4.text = self.name
                self.parent.plot.append(MeshLinePlot(color = [0.11,0.95,0.93,1]))
                self.parent.parent.manager.get_screen('almsc').ids.grafi.add_plot(self.parent.plot[3])
                if self.ch > self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax:
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.ymax = self.ch + 20
                    self.parent.parent.manager.get_screen('almsc').ids.grafi.y_ticks_major = (self.ch + 20)/10

    def measure(self):
        Clock.schedule_interval(self.setbar, 60/60.)

    def setbar(self, *args):
        if self.pin.read()==None:
            self.value=0
        else:
            a = self.ch-self.cl
            self.value = (a*self.pin.read())+self.cl
        if self.graphable:
            self.plp.append(self.value)
            self.parent.uplot(self.name,self.plp)
        self.beep()

    def beep(self,*args):
        if self.value >= self.ch:
            self.alarming = True
            self.parent.rise(self.name,self.value,'HH',self.desc)
            if not self.parent.parent.manager.current == 'almsc':
                    if self.parent.tone3:
                            self.parent.tone3.play()
        elif self.value <= self.cl:
            self.alarming = True
            self.parent.rise(self.name,self.value,'LL',self.desc)
    	    if not self.parent.parent.manager.current == 'almsc':
                if self.parent.tone3:
                    self.parent.tone3.play()
        elif self.value < self.l and self.value > self.cl:
            self.alarming = True
            self.parent.rise(self.name,self.value,'L', self.desc)
            if not self.parent.parent.manager.current == 'almsc':
                if self.parent.tone1:
                    self.parent.tone1.play()
        elif self.value > self.h and self.value < self.ch:
            self.alarming = True
            self.parent.rise(self.name,self.value,'H',self.desc)
            if not self.parent.parent.manager.current == 'almsc':
                if self.parent.tone1:
                    self.parent.tone1.play()
        else:
            self.alarming = False

    def end(self,*args):
        Clock.unschedule(self.setbar)

    def on_touch_up(self,touch):
        super(Ingageh, self).on_touch_up(touch)
        if self.collide_point(touch.x,touch.y):
            if touch.is_double_tap and not self.parent.running and not self.ass:
                q = session.query(RTU).first()
                if q == None:
                    hey = Tempop(title = 'Empty database')
                    hey.ids['yo'].text = 'Nothing to link'
                    hey.open()
                else:
                    rs = session.query(RTU).all()
                    DBpop = DBPopup(target_element = self, typ = 'a')
                    for r in rs:
                        ans = session.query(Apoint).filter(Apoint.AP_RTUid==r.RTU_id).all()
                        DBpop.ids['ptspin1'].rvalues[r.RTU_name] = []
                        for an in ans:
                            if an.AP_tag not in self.parent.asspts:
                                DBpop.ids['ptspin1'].rvalues[r.RTU_name].append(an.AP_tag)
                        DBpop.ids['rspin'].values.append(r.RTU_name)
                    DBpop.open()

    def restart(self,*args):
        self.value=0

# Next two classes are analogic output bars containing two widgets: a modified
# Ingage and a slider. Some of the methods here may appear unnecessary at first
# glance but most of them prevent behavior errors betwen these two elements
# (ingage and slider)
class Outgage(DragBehavior, Widget):
    name=StringProperty()
    desc=StringProperty()
    val=NumericProperty()
    rem=ObjectProperty()
    pinmo=StringProperty()
    pin=ObjectProperty()
    note = StringProperty()
    sel = BooleanProperty(False)
    selectable = BooleanProperty(True)
    # Establishes that widget contains a slider
    slide = BooleanProperty(True)
    # Slider value that sets ingage level
    cntv = NumericProperty()
    ass = BooleanProperty(False)
    unit = StringProperty()
    ptyp = StringProperty('p')
    pinno = StringProperty()

    # Clock for scheduling control actions
    def measure(self,*args):
        Clock.schedule_interval(self.control,60/60.)

    # Writes current value to linked point
    def control(self, *args):
        a = self.ids['cnt'].max-self.ids['cnt'].min
        self.val = (self.ids['cnt'].value-self.ids['cnt'].min)/a
        if not self.parent.ftrun:
            self.pin.write(self.val)

    # Opens linking popup
    def on_touch_down(self,touch):
        if self.ids['cnt'].collide_point(touch.x, touch.y) and not self.parent.running:
            pass
        if not self.parent.running:
            if self.collide_point(touch.x,touch.y) and touch.is_double_tap and not self.ass:
                q = session.query(RTU).first()
                if q == None:
                    hey = Tempop(title = 'Empty database')
                    hey.ids['yo'].text = 'Nothing to link'
                    hey.open()
                else:
                    rs = session.query(RTU).all()
                    DBpop = DBPopup(target_element = self, typ = 'p')
                    for r in rs:
                        ps = session.query(Ppoint).filter(Ppoint.PP_RTUid==r.RTU_id).all()
                        DBpop.ids['ptspin1'].rvalues[r.RTU_name] = []
                        for p in ps:
                            if p.PP_tag not in self.parent.asspts:
                                DBpop.ids['ptspin1'].rvalues[r.RTU_name].append(p.PP_tag)
                        DBpop.ids['rspin'].values.append(r.RTU_name)
                    DBpop.open()

    # Method that distinguishes when the widget is being dragged across the
    # screen from when only the slider is being dragged
    def on_touch_move(self, touch):
        if self.ids['cnt'].collide_point(touch.x, touch.y):
            if self.parent.running:
                self.cntv = self.ids['cnt'].value_normalized
            else:
                pass
        else:
            super(Outgage, self).on_touch_move(touch)

    def end(self,*args):
        Clock.unschedule(self.control)

# Horizontal bar
class Outgageh(DragBehavior, Widget):
    name=StringProperty()
    desc=StringProperty()
    val=NumericProperty()
    rem=ObjectProperty()
    pinno=NumericProperty()
    pinmo=StringProperty()
    pin=ObjectProperty()
    note = StringProperty()
    sel = BooleanProperty(False)
    selectable = BooleanProperty(True)
    slide = BooleanProperty(True)
    cntv = NumericProperty()
    ass = BooleanProperty(False)
    unit = StringProperty()
    ptyp = StringProperty('p')
    pinno = StringProperty()

    def measure(self,*args):
        Clock.schedule_interval(self.control,60/60.)

    def control(self, *args):
        a= self.ids['cnt'].max-self.ids['cnt'].min
        self.val = (self.ids['cnt'].value-self.ids['cnt'].min)/a
        if not self.parent.ftrun:
            self.pin.write(self.val)

    def on_touch_down(self,touch):
        if self.ids['cnt'].collide_point(touch.x, touch.y) and not self.parent.running:
            pass
        if not self.parent.running:
            if self.collide_point(touch.x,touch.y) and touch.is_double_tap and not self.ass:
                q = session.query(RTU).first()
                if q == None:
                    hey = Tempop(title = 'Empty database')
                    hey.ids['yo'].text = 'Nothing to link'
                    hey.open()
                else:
                    rs = session.query(RTU).all()
                    DBpop = DBPopup(target_element = self, typ = 'p')
                    for r in rs:
                        ps = session.query(Ppoint).filter(Ppoint.PP_RTUid==r.RTU_id).all()
                        DBpop.ids['ptspin1'].rvalues[r.RTU_name] = []
                        for p in ps:
                            if p.PP_tag not in self.parent.asspts:
                                DBpop.ids['ptspin1'].rvalues[r.RTU_name].append(p.PP_tag)
                        DBpop.ids['rspin'].values.append(r.RTU_name)
                    DBpop.open()

    def on_touch_move(self, touch):
        if self.ids['cnt'].collide_point(touch.x, touch.y):
            if self.parent.running:
                self.cntv = self.ids['cnt'].value_normalized
            else:
                pass
        else:
            super(Outgageh, self).on_touch_move(touch)

    def end(self,*args):
        Clock.unschedule(self.control)

# Draggable textbox
class Textbox(TextInput):
    selectable = BooleanProperty(True)
    # Indicates that widget is a textbox
    textable = BooleanProperty(True)
    # Indicates if widget is current selection
    sel = BooleanProperty(False)
    ass = BooleanProperty(False)

# linking popup
class DBPopup(Popup):
    # Stores the widget to link
    target_element = ObjectProperty()
    # Indicates the caller widget type
    typ = StringProperty()

    # Method that sets the widget properties according to linked point
    def save(self):
        # linking of digital widget
        if self.typ == 'd':
            r_info = session.query(RTU).filter(RTU.RTU_name==self.ids['rspin'].text).first()
            p_info = session.query(Dpoint).filter(Dpoint.DP_RTUid == r_info.RTU_id, Dpoint.DP_tag == self.ids['ptspin1'].text).one()
            self.target_element.RTU = self.ids['rspin'].text
            self.target_element.pinmo = p_info.DP_pinmo
            self.target_element.pinno = str(p_info.DP_pinno)
            self.target_element.desc = p_info.DP_descrip
            self.target_element.alarmer = p_info.DP_alarmer
            self.target_element.value = 0
            self.target_element.name = self.ids['ptspin1'].text
            self.target_element.ass = True
            self.target_element.parent.asspts.append(p_info.DP_tag)
        # linking of analogic input widget
        elif self.typ == 'a':
            r_info = session.query(RTU).filter(RTU.RTU_name==self.ids['rspin'].text).first()
            p_info = session.query(Apoint).filter(Apoint.AP_RTUid==r_info.RTU_id,Apoint.AP_tag==self.ids['ptspin1'].text).first()
            self.target_element.RTU = self.ids['rspin'].text
            self.target_element.desc= p_info.AP_descrip
            self.target_element.pinmo = p_info.AP_pinmo
            self.target_element.pinno = str(p_info.AP_pinno)
            self.target_element.ch = float(p_info.AP_chilimit)
            self.target_element.cl = float(p_info.AP_clowlimit)
            self.target_element.h = float(p_info.AP_hilimit)
            self.target_element.l = float(p_info.AP_lowlimit)
            self.target_element.graphable = p_info.AP_graph
            if self.target_element.graphable and not self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog1.active:
                self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog1.active = True
            elif not self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog2.active:
                self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog2.active = True
            elif not self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog3.active:
                self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog3.active = True
            else:
                self.target_element.parent.parent.manager.get_screen('almsc').ids.gtog4.active = True
            self.target_element.unit = p_info.AP_unit
            self.target_element.name = self.ids['ptspin1'].text
            self.target_element.value = 0
            self.target_element.setgraph()
            self.target_element.ass = True
            self.target_element.parent.asspts.append(p_info.AP_tag)
        # Analogic output widget linking
        elif self.typ == 'p':
            r_info = session.query(RTU).filter(RTU.RTU_name==self.ids['rspin'].text).first()
            p_info = session.query(Ppoint).filter(Ppoint.PP_RTUid==r_info.RTU_id,Ppoint.PP_tag==self.ids['ptspin1'].text).first()
            self.target_element.desc= p_info.PP_descrip
            self.target_element.pinmo = p_info.PP_pinmo
            self.target_element.pinno = str(p_info.PP_pinno)
            self.target_element.ids['cnt'].max= p_info.PP_max
            self.target_element.ids['cnt'].min= p_info.PP_min
            self.target_element.name = self.ids['ptspin1'].text
            self.target_element.unit = p_info.PP_unit
            self.target_element.ass = True
            self.target_element.parent.asspts.append(p_info.PP_tag)
            self.target_element.control()

# Spinner which contents are updated based on external events. It is used on
# DBpopup to show points existing in a remote, when the selected remote changes
# the content of this spinner also changes
class Ptspin(Spinner):
    # Dict that contains each remote with its points
    rvalues = ObjectProperty()

    # Declaring rvalues as a dict on init
    def __init__(self, **kwargs):
        super(Ptspin, self).__init__(**kwargs)
        self.rvalues = {}

    # Method that changes the spinner's contents
    def upvalues(self, rm, *args):
        self.values = self.rvalues[rm]

# Display toolbar
class Toolbar(GridLayout):
    pass

# MyLayout is the core of the HMI. It manages animations, plotting and alarms
# All existing widgets on a display are children to this object
class MyLayout(Widget, CompoundSelectionBehavior):
    # Present remotes list (as pyFirmata objects)
    ard = ListProperty()
    # Iterator for pyFirmata
    it = ListProperty()
    # Indicates if a scan is initiated
    running = BooleanProperty(False)
    # Current time and date for display
    rtime = StringProperty()
    rdate = StringProperty()
    # Stores the currently selected element
    selected = ObjectProperty()
    # Dashed box that is drawn around a selected element
    touches = ObjectProperty()
    # Indicates if an element is currently selected
    selmn = BooleanProperty(False)
    # Initial position of a draggable widget
    st = ListProperty()
    # Plots for the trends screen
    plot = ListProperty()
    # Points for the plots
    toplot = ObjectProperty()
    # Alarm sounds
    tone1 = ObjectProperty()
    tone2 = ObjectProperty()
    tone3 = ObjectProperty()
    # linked points list
    asspts = ListProperty()
    # List of linked widgets
    toscan = ListProperty()
    # Indicates if scan is running for the first time
    ftrun = BooleanProperty()

    # On init, toplot is declared as a dict and date/time are displayed
    def __init__(self, **kwargs):
        self.toplot = {}
        Clock.schedule_interval(self.settime, 1)
        super(MyLayout, self).__init__(**kwargs)

    # Click override to ignore clicks on the toolbar while scan is running
    def on_touch_down(self,touch):
        super(MyLayout, self).on_touch_down(touch)
        if touch.x < 100 and self.running:
            pass

    # Widget creation override to:
    # 1 - Give widget_touch_down and widget_move to new widgets
    # 2 - autoselect last created widget
    def add_widget(self, widget):
        try:
            if self.selmn:
                self.canvas.after.remove(self.touches)
            if widget.selectable:
                try:
                    self.selected.sel = False
                except:
                    pass
                widget.bind(on_touch_down = self.widget_touch_down,
                            on_touch_move = self.widget_move)
                self.selected = widget
                widget.sel = True
                self.selmn = True
                with self.canvas.after:
                    Color(0,0,0,1)
                    self.touches=Line(rectangle=(widget.x-5,
                        widget.y-5,widget.width+10,widget.height+10),
                        dash_length=5,dash_offset=2)
                return super(MyLayout, self).add_widget(widget)
        except:
            return super(MyLayout, self).add_widget(widget)

    # Remove method override to clear linked points list
    def remove_widget(self,widget):
        super(MyLayout, self).remove_widget(widget)
        if widget.ass:
            self.asspts.pop(self.asspts.index(widget.name))

    # Selection filter method, when a widget is clicked:
    # 1 - Deselects it if currently selected
    # 2 - If other is selected, deselects and selects the clicked-on widget
    # 3 - Simply selects if there's no other widget selected
    def widget_touch_down(self, widget, touch):
        if not self.running:
            if widget.collide_point(*touch.pos):
                if self.selmn and widget.sel:
                    widget.sel = False
                    self.selmn = False
                    self.canvas.after.remove(self.touches)
                elif self.selmn and not widget.sel:
                    self.selected.sel = False
                    self.canvas.after.remove(self.touches)
                    self.selected = widget
                    widget.sel = True
                    with self.canvas.after:
                        Color(0,0,0,1)
                        self.touches=(Line(rectangle=(widget.x-5,
                            widget.y-5, widget.width+10, widget.height+10),
                            dash_length=5,dash_offset=2))
                    self.st = widget.pos
                elif not self.selmn:
                    widget.sel = True
                    self.selected = widget
                    self.selmn = True
                    with self.canvas.after:
                        Color(0,0,0,1)
                        self.touches=Line(rectangle=(widget.x-5,
                            widget.y-5, widget.width+10, widget.height+10),
                            dash_length=5,dash_offset=2)
                    self.st = widget.pos
        else:
            try:
                if not widget.ids['cnt'].orientation == 'vertical':
                    return super(Outgageh, widget).on_touch_down(touch)
                else:
                    return super(Outgage, widget).on_touch_down(touch)
            except:
                pass

    # Click release override to deselect when empty space is clicked
    def on_touch_up(self, touch):
        if self.running and touch.x < 100:
            pass
        tching = False
        if touch.x > 100:
            if self.selected == None:
                pass
            else:
                if self.st != self.selected.pos:
                    self.st = self.selected.pos
                else:
                    for kid in self.children:
                        try:
                            if kid.selectable:
                                if kid.collide_point(*touch.pos):
                                    tching = True
                        except: pass
                    if not tching and self.selmn:
                        self.selmn = False
                        self.canvas.after.remove(self.touches)
                        for k in self.children:
                            try:
                                if k.selectable:
                                    k.sel = False
                            except: pass
            super(MyLayout, self).on_touch_up(touch)

    # Method to move selection with widget
    def widget_move(self, widget, touch):
        if not self.running:
            if widget.collide_point(*touch.pos):
                self.canvas.after.remove(self.touches)
                child = self.selected
                child.center = touch.pos
                child.sel = True
                self.selmn = True
                with self.canvas.after:
                    Color(0,0,0,1)
                    self.touches=Line(rectangle=(child.x-5,child.y-5,
                    child.width+10,child.height+10),width=1,
                    dash_length=5,dash_offset=2)

    # Method that controls the subtype selection popups
    def selpop(self, typ, *args):
        if typ == 'd':
            sel = Selectpop(caller = self, typ = typ)
        elif typ == 'a':
            sel = Selectpop(caller = self, title = 'Select analogic', typ = typ)
            sel.ids['i1'].source = os.getcwd() + '/imgs/dvbarfull.png'
            sel.ids['i1'].size = (20, 60)
            sel.ids['i2'].source = os.getcwd() + '/imgs/dhbarfull.png'
            sel.ids['i2'].size = (60, 20)
            sel.ids['i3'].source = os.getcwd() + '/imgs/tankbar.png'
            sel.ids['i3'].size = (50, 150)
        else:
            sel = Selectpop(caller = self, title = 'Select analogic', typ = typ)
            sel.ids['i1'].source = os.getcwd() + '/imgs/barslider.png'
            sel.ids['i1'].size = (40, 160)
            sel.ids['i2'].source = os.getcwd() + '/imgs/hbarslider.png'
            sel.ids['i2'].size = (160, 40)
            sel.ids['i3'].source = os.getcwd() + '/imgs/nope.png'
            sel.ids['i3'].size = (60, 60)
        sel.open()

    # Method to add a new blinker
    def newblinker(self, sele, *args):
        if sele == os.getcwd() + '/imgs/blinkeron.png':
            blink1=Blinker(center=self.center, size= (30, 30))
            blink1.canvas.get_group('icon')[0].source = os.getcwd() +'/imgs/blinker.png'
        elif sele == os.getcwd() + '/imgs/valveon.png':
            blink1=Blinker(center=self.center, size= (60, 60))
            blink1.canvas.get_group('icon')[0].source = os.getcwd() + '/imgs/valve1.png'
        else:
            blink1 = Blinker(center=self.center, size= (50, 50))
            blink1.canvas.get_group('icon')[0].source = os.getcwd() + '/imgs/pump1.png'
        self.add_widget(blink1)

    # Method to add a new outgage
    def newogage(self, sele, *args):
        if sele == os.getcwd() + '/imgs/barslider.png':
            gage1 = Outgage(center = self.center, size = (25, 100))
            self.add_widget(gage1)
        elif sele == os.getcwd() + '/imgs/hbarslider.png':
            gage1 = Outgageh(center = self.center, size = (100, 25))
            self.add_widget(gage1)
        elif sele == os.getcwd() + '/imgs/nope.png':
            hey = Tempop(title = 'Not available')
            hey.ids['yo'].text = 'Select a valid element'
            hey.open()

    # Method to add a new ingage
    def newigage(self, sele, *args):
        if sele == os.getcwd() + '/imgs/tankbar.png':
            gage1 = Ingage(center = self.center, size = (25, 100))
        elif sele == os.getcwd() + '/imgs/dhbarfull.png':
            gage1 = Ingageh(center = self.center, size = (100, 25))
        else:
            gage1 = Ingage(center = self.center, size = (25, 100))
            gage1.remove_widget(gage1.ids['tank'])
        self.add_widget(gage1)

    # Method to add a new textbox
    def textbox(self, *args):
        tb = Textbox(center = self.center)
        tb.focus = True
        tb.bind(text = self.resizebox)
        self.add_widget(tb)

    # Method that adjust textbox size to contained text
    def resizebox(self, *args):
        for kid in self.children:
            try:
                if kid.textable and kid.sel:
                    self.canvas.after.remove(self.touches)
                    with self.canvas.after:
                        Color(0,0,0,1)
                        self.touches=(Line(rectangle=(kid.x-5,
                                kid.y-5, kid.width+10, kid.height+10),
                                dash_length=5,dash_offset=2))
            except: continue

    def portsel(self, *args):
        qs = session.query(RTU).all()
        if self.ftrun:
            if len(qs) == 0:
                hey = Tempop(title = 'Error')
                hey.ids['yo'].text = 'No remotes found'
                hey.open()
            elif len(self.asspts) == 0:
                hey = Tempop(title = 'Error')
                hey.ids['yo'].text = 'No linked elements'
                hey.open()
            else:
                for q in qs:
                    newppop = Portpop(caller = self, myrem = q.RTU_name)
                    newppop.open()
        else:
            ###########!!!!!!
            for q in qs:
                self.caniscan(q.RTU_name)

    # Method to check if running conditions are met
    def caniscan(self, myrem, *args):
        if not self.running:
            gels = 0
            assels = 0
            for kid in self.children:
                try:
                    if kid.ass:
                        assels += 1
                        self.toscan.append(kid)
                    if kid.graphable:
                        gels += 1
                except: continue
            if assels > 0 and gels > 0 and self.ftrun:
                self.setcomm(True, myrem)
            elif assels > 0 and gels == 0 and self.ftrun:
                self.setcomm(False, myrem)
            else:
                self.startall()
                self.startgraph()

    def setcomm(self, gr, myrem, *args):
        if self.ard == []:
            r_info = session.query(RTU).filter(RTU.RTU_name == myrem).first()
            self.ard.append(Arduino(r_info.RTU_port))
            self.it.append(util.Iterator(self.ard[0]))
            self.it[0].start()
        for kid in self.toscan:
            kid.pin = self.ard[0].get_pin('{0}:{1}:{2}'.format(kid.ptyp,kid.pinno,kid.pinmo[0].lower()))
        self.startall()
        if gr:
            self.startgraph()

    # Method that starts firmata queries and animations
    def startall(self, *args):
        self.running = True
        self.ftrun = False
        for kid in self.toscan:
            kid.measure()
            kid.drag_distance = 0
            kid.drag_rectangle = 0,0,0,0
            kid.slide = False
        Clock.schedule_interval(self.savetodb, 5)
        self.canvas.after.remove(self.touches)

    # Method that updates date and time in real time
    def settime(self,*args):
        self.rtime = time.strftime('%H:%M:%S')
        self.rdate = time.strftime('%d/%m/%Y')

    # Stops queries and animation
    def stahp(self,*args):
        if self.running:
            self.running = False
            for kid in self.toscan:
                kid.end()
            Clock.unschedule(self.savetodb)
            self.startgraph()
        else:
            pass

    # Resets animations
    def reset(self,*args):
        self.running=False
        for kid in self.children:
            try: kid.restart()
            except: continue

    # Raises an alarm
    def rise(self, tag, val, typ, des):
        self.ids['almb'].y = 30
        self.parent.manager.get_screen('almsc').ids.alms.newalm(tag,val,typ,self.rtime, des)

    # Real-time plot update
    def uplot(self,tag,vals,*args):
        self.toplot[tag] = vals

    # Sends points contained in toplot for plotting
    def plotel(self,*args):
        for key in self.toplot:
            if key == self.parent.manager.get_screen('almsc').ids.pl1.text and self.parent.manager.get_screen('almsc').ids.gtog1.active:
                self.plot[0].points = [(i,j) for i, j in enumerate(self.toplot[key])]
            elif key == self.parent.manager.get_screen('almsc').ids.pl2.text and self.parent.manager.get_screen('almsc').ids.gtog2.active:
                self.plot[1].points = [(i,j) for i, j in enumerate(self.toplot[key])]
            elif key == self.parent.manager.get_screen('almsc').ids.pl3.text and self.parent.manager.get_screen('almsc').ids.gtog3.active:
                self.plot[2].points = [(i,j) for i, j in enumerate(self.toplot[key])]
            elif key == self.parent.manager.get_screen('almsc').ids.pl4.text and self.parent.manager.get_screen('almsc').ids.gtog4.active:
                self.plot[3].points = [(i,j) for i, j in enumerate(self.toplot[key])]

    # Plotting clocks: Plotting, x-axis labels update and range expansion
    def startgraph(self):
        if not self.parent.manager.get_screen('almsc').ids.ATbox.plotting:
            Clock.schedule_interval(self.plotel, 1)
            Clock.schedule_interval(self.parent.manager.get_screen('almsc').ids.ATbox.expand, 60)
            Clock.schedule_once(self.parent.manager.get_screen('almsc').ids.ATbox.sethms)
            self.parent.manager.get_screen('almsc').ids.ATbox.plotting = True
        else:
            Clock.unschedule(self.plotel)
            Clock.unschedule(self.parent.manager.get_screen('almsc').ids.ATbox.expand)
            self.parent.manager.get_screen('almsc').ids.ATbox.plotting = False

    # Writes readings each minute to database
    def savetodb(self, *args):
        rinfo = session.query(RTU).first()
        stime = self.rtime
        for kid in self.children:
            try:
                if kid.selectable:
                    dinfo = session.query(Dpoint).filter(Dpoint.DP_RTUid == rinfo.RTU_id, Dpoint.DP_tag == kid.name).first()
                    ainfo = session.query(Apoint).filter(Apoint.AP_RTUid == rinfo.RTU_id, Apoint.AP_tag == kid.name).first()
                    pinfo = session.query(Ppoint).filter(Ppoint.PP_RTUid == rinfo.RTU_id, Ppoint.PP_tag == kid.name).first()
                    if ainfo == None and pinfo == None:
                        dread = Pread(PR_val = kid.value, PR_typ = 'd', PR_time = stime)
                        dread.Rdp = dinfo
                        session.add(dread)
                    elif dinfo == None and pinfo == None:
                        aread = Pread(PR_val = kid.value, PR_typ = 'a', PR_time = stime)
                        aread.Rap = ainfo
                        session.add(aread)
                    elif dinfo == None and ainfo == None:
                        pmread = Pread(PR_val = kid.ids['cnt'].value, PR_typ = 'p', PR_time = stime)
                        pmread.Rpp = pinfo
                        session.add(pmread)
            except: continue
        session.commit()

    # Opens read reporting popup
    def repop(self, *args):
        rep = Savepop(caller = self, preporter = True)
        rep.open()

    # Generates readings report
    def reportdb(self, txt, *args):
        if not txt.endswith('.txt'):
            txt = txt + '.txt'
        if os.path.isfile(os.getcwd() + '/Reports/' + txt):
            nope = Tempop(title = 'Error')
            nope.ids['yo'].text = 'Duplicated file name'
            nope.open()
        else:
            rdrp = OrderedDict()
            rpfl = open(os.getcwd() + '/Reports/' + txt, 'w+')
            reads = session.query(Pread).all()
            for read in reads:
                if read.PR_time not in rdrp.keys():
                    rdrp[read.PR_time] = []
            for key in rdrp.keys():
                for read in reads:
                    if read.PR_time == key:
                        if read.PR_typ == 'd':
                            dtag = session.query(Dpoint).filter(Dpoint.DP_id == read.PR_dpointid).first().DP_tag
                            rdrp[key].append((read.PR_val, dtag))
                        elif read.PR_typ == 'a':
                            atag = session.query(Apoint).filter(Apoint.AP_id == read.PR_apointid).first().AP_tag
                            rdrp[key].append((read.PR_val, atag))
                        elif read.PR_typ == 'p':
                            ptag = session.query(Ppoint).filter(Ppoint.PP_id == read.PR_ppointid).first().PP_tag
                            rdrp[key].append((read.PR_val, ptag))
            for key, values in rdrp.items():
                rpfl.write(key + '\r')
                for value in values:
                    rpfl.write(value[1] + ', ' + str(value[0]) + '; ')
                rpfl.write('\r\n')
            rpfl.close()
            hey = Tempop(title = 'Success')
            hey.ids['yo'].text = 'Report created'
            hey.open()

    # Opens background image selector
    def bgpop(self, *args):
        imsel = Chpop(caller = self, imager = True)
        imsel.open()

    # Establishes backgroung image
    def setbg(self, pt, ima, *args):
        with self.canvas.before:
            Rectangle(pos = self.pos, size = self.size, source = os.path.join(pt, ima[0]))

############# Alarms/Trends screen
# Only manages alarm reports
class AlarmScreen(Screen):

    # Alarm report popup
    def alpop(self, *args):
        alport = Savepop(caller = self, areporter = True)
        alport.open()

    def reportal(self, txt, *args):
        if not txt.endswith('.txt'):
            txt = txt + '.txt'
        if os.path.isfile(os.getcwd() + '/Reports/' + txt):
            nope = Tempop(title = 'Error')
            nope.ids['yo'].text = 'Duplicated file name'
            nope.open()
        else:
            rpfl = open(os.getcwd() + '/Reports/' + txt, 'w+')
            als = session.query(Alarm).all()
            for al in als:
                if al.AL_typ == 'd':
                    rpfl.write(al.AL_time + '\r' + str(al.dal.DP_tag) + '; ' + str(al.AL_value) + '; ' + al.AL_typ + '\r\n')
                else:
                    rpfl.write(al.AL_time + '\r' + str(al.aal.AP_tag) + '; ' + str(al.AL_value) + '; ' + al.AL_typ + '\r\n')
            rpfl.close()

# Inherits from Lista class (see database screen). Changes made are for alarm
# recognition
class Alarms(Lista):
    # alarms present in the list
    curr = ListProperty()

    # Includes a new alarm depending on the element raising it
    def newalm(self, tag, val, typ, tm, des):
        if val not in self.curr:
            rinf = session.query(RTU).first()
            dinf = session.query(Dpoint).filter(Dpoint.DP_RTUid == rinf.RTU_id, Dpoint.DP_tag == tag).first()
            ainf = session.query(Apoint).filter(Apoint.AP_RTUid == rinf.RTU_id, Apoint.AP_tag == tag).first()
            if ainf == None:
                alm = Alarm(AL_time = self.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.rtime,
                            AL_typ = typ,
                            AL_value = val)
                alm.dal = dinf
                session.add(alm)
                session.commit()
            elif dinf == None:
                alm = Alarm(AL_time = self.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.rtime,
                            AL_typ = typ,
                            AL_value = val)
                alm.aal = ainf
                session.add(alm)
                session.commit()
            nalm = BoxLayout(spacing = 20, size_hint_y = None, height = 30)
            self.curr.append(val)
            t = Label(text = tm, color = (0,0,0,1))
            nm = Label(text = tag, color = (0,0,0,1))
            vl = Blklb(text = str(val), color = (0,0,0,1))
            ds = Label(text = des, color = (0,0,0,1))
            if typ == 'L' or typ == 'H':
                ev = Label(text = typ, color=(1,1,0,1))
            elif typ == 'LL' or typ == 'HH':
                ev = Label(text = typ, color=(1,0,0,1))
            elif typ == 'd':
                ev = Label(text = 'Ha cambiado de estado', color = (0,0,0,1))
            nalm.add_widget(t)
            nalm.add_widget(nm)
            nalm.add_widget(vl)
            nalm.add_widget(ev)
            nalm.add_widget(ds)
            vl.mytag = tag
            self.add_widget(nalm)

# Blinking label
class Blklb(Label):
    # Indicates if label is currently highlighted
    hlted = BooleanProperty(False)
    # tag associated with label
    mytag = StringProperty()

    # Schedules blinking on init
    def __init__(self, **kwargs):
        super(Blklb, self).__init__(**kwargs)
        Clock.schedule_interval(self.blink, 1)

    # BLink mechanics
    def blink(self, *args):
        if not self.hlted:
            with self.canvas.before:
                Color(*(1,1,1,0.75))
                Rectangle(pos = self.pos, size = self.size)
            self.hlted = True
        else:
            with self.canvas.before:
                Color(*(get_color_from_hex('#87FFFC')))
                Rectangle(pos = self.pos, size = self.size)
            self.hlted = False

    # Alarm recognition mechanics on click:
    # If widget is still on alarm state, blinking stops but alarm stays on list
    # If widget is not on alarm state, alarm disappears from the list
    def on_touch_down(self, touch):
        super(Blklb, self).on_touch_down(touch)
        if self.parent.collide_point(touch.x, touch.y):
            for kid in self.parent.parent.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.children:
                try:
                    if kid.name == self.mytag and kid.alarming:
                        Clock.unschedule(self.blink)
                        self.canvas.before.clear()
                    elif kid.name == self.mytag and not kid.alarming:
                        Clock.unschedule(self.blink)
                        self.parent.parent.remove_widget(self.parent)
                        self.canvas.before.clear()
                except:
                    continue
            if self.text == '1' or self.text == '0':
                self.parent.parent.remove_widget(self.parent)
                self.canvas.before.clear()

# Plotting area class
class PlotArea(BoxLayout):
    plotime = StringProperty()
    strtime = ListProperty()
    numtime = ListProperty()
    timeset = BooleanProperty(False)
    plotting = BooleanProperty(False)

    def expand(self, *args):
        self.parent.parent.ids['grafi'].xmax = self.parent.parent.ids['grafi'].xmax + 60
        for num in range(len(self.numtime[1:6])):
            self.numtime[num + 1] = self.numtime[num + 1] + (12 * (num + 1))
        strt = []
        for nt in self.numtime[1:6]:
            strt.append([str(nt/3600), ':' + str((nt%3600)/60) + ':', str((nt%3600)%60)])
        self.tmcon(strt)

    def sethms(self, *args):
        if not self.timeset:
            ini = time.strftime('%H:%M:%S')
            self.strtime.append(ini)
            ini = ini.split(':')
            ininum = (int(ini[0])*3600)+(int(ini[1])*60)+int(ini[2])
            self.numtime.append(ininum)
            strt = []
            for i in range(5):
                ininum = ininum + 10
                self.numtime.append(ininum)
                strt.append([str(ininum/3600), ':' + str((ininum%3600)/60) + ':', str((ininum%3600)%60)])
            self.tmcon(strt)
            self.timeset = True

    def tmcon(self, itv):
        if len(self.strtime) > 1:
            for st in self.strtime[1:6]:
                self.strtime.pop(self.strtime.index(st))
        for tm in itv:
            for t in tm:
                if len(t) == 1:
                    tm.insert(tm.index(t) + 1, '0' + t)
                    tm.pop(tm.index(t))
                elif len(t) == 3:
                    tm.insert(tm.index(t) + 1, ':' + '0' + t.lstrip(':'))
                    tm.pop(tm.index(t))
            self.strtime.append(tm[0] + tm[1] + tm[2])
        n = 1
        for ts in self.strtime:
            self.parent.parent.ids['t' + str(n)].text = ts
            n += 1

# Checkbox that plots/unplots values from selected/unselected element
class Gcheck(CheckBox):
    myplot = StringProperty()

    def on_active(self, *args):
        super(Gcheck, self).on_active(*args)
        if not self.active and self.parent.parent.parent.parent.parent.ids['ATbox'].plotting:
            Clock.unschedule(self.parent.parent.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.plotel)
            self.parent.parent.parent.parent.parent.ids['grafi'].remove_plot(self.parent.parent.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.plot[int(self.myplot)])
        elif self.active and self.parent.parent.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.running:
            Clock.schedule_interval(self.parent.parent.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.plotel, 0.2)
            self.parent.parent.parent.parent.parent.ids['grafi'].add_plot(self.parent.parent.parent.parent.parent.manager.get_screen('ihmsc').ids.ihm.plot[int(self.myplot)])

################# Final App class and execution
# Loads the .kv file (widget tree structure)
Builder.load_file('wtree.kv')

# Establishes the screenmanager, in charge of transition and interscreen
# interaction
sm=ScreenManager()
# Including each screen on the ScreenManager and naming them
sm.add_widget(Prescreen(name = 'psc'))
sm.add_widget(DBScreen(name = 'dbsc'))
sm.add_widget(HMIscreen(name = 'ihmsc'))
sm.add_widget(AlarmScreen(name = 'almsc'))

# Final app building
class microIHMApp(App):
    def build(self):
        return sm

    # Method to shut communications with the microcontroller when apps is closed
    def on_stop(self, **kwargs):
        super(microIHMApp, self).on_stop(**kwargs)
        if not self.root_window.children[0].get_screen('ihmsc').ids['ihm'].ard == []:
            self.root_window.children[0].get_screen('ihmsc').ids['ihm'].ard[0].exit()

# execution
if __name__=='__main__':
    microIHMApp().run()
