# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 Exporter Framework - LuxRender Plug-in
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****
#
import threading
import datetime

import bpy

from ef.ef import ef

# CHOOSE API TYPE
import luxrender.module.pure_api    # Access lux only through pylux bindings
import luxrender.module.file_api    # Write conventional lx* files and use pylux to manage lux process

def LuxLog(*args):
    '''
    Send string to EF log, marked as belonging to LuxRender module.
    Accepts variable args (can be used as pylux.errorHandler)
    '''
    if len(args) > 0:
        ef.log(' '.join(['%s'%a for a in args]), module_name='Lux')

class LuxOutput(object):
    '''
    Base class for any Lux output
    '''
    pass

class LuxFile(LuxOutput):
    '''
    Write to LXS file
    '''
    
    pass
    
class LuxTimerThread(threading.Thread):
    '''
    Periodically call self.kick()
    '''
    KICK_PERIOD = 8
    
    active = True
    timer = None
    
    lux_context = None
    
    def __init__(self, lux_context):
        threading.Thread.__init__(self)
        self.lux_context = lux_context
    
    def stop(self):
        self.active = False
        if self.timer is not None:
            self.timer.cancel()
            
    def run(self):
        '''
        Timed Thread loop
        '''
        
        while self.active:
            self.timer = threading.Timer(self.KICK_PERIOD, self.kick)
            self.timer.start()
            if self.timer.isAlive(): self.timer.join()
            
    def kick(self):
        '''
        sub-classes do their work here
        '''
        pass
    

def format_elapsed_time(t):
    td = datetime.timedelta(seconds=t)
    min = td.days*1440  + td.seconds/60.0
    hrs = td.days*24    + td.seconds/3600.0
    
    return '%i:%02i:%02i' % (hrs, min%60, td.seconds%60)

class LuxAPIStats(LuxTimerThread):
    '''
    Periodically get lux stats
    '''
    
    KICK_PERIOD = 1
    
    stats_dict = {
        'secElapsed':       0.0,
        'samplesSec':       0.0,
        'samplesTotSec':    0.0,
        'samplesPx':        0.0,
        'efficiency':       0.0,
        #'filmXres':         0.0,
        #'filmYres':         0.0,
        #'displayInterval':  0.0,
        'filmEV':           0.0,
        #'sceneIsReady':     0.0,
        #'filmIsReady':      0.0,
        #'terminated':       0.0,
    }
    
    stats_format = {
        'secElapsed':       format_elapsed_time,
        'samplesSec':       lambda x: 'Samples/Sec: %0.2f'%x,
        'samplesTotSec':    lambda x: 'Total Samples/Sec: %0.2f'%x,
        'samplesPx':        lambda x: 'Samples/Px: %0.2f'%x,
        'efficiency':       lambda x: 'Efficiency: %0.2f %%'%x,
        'filmEV':           lambda x: 'EV: %0.2f'%x,
    }
    
    stats_string = ''
    
    def stop(self):
        self.active = False
        if self.timer is not None:
            self.timer.cancel()
            
    def kick(self):
        for k in self.stats_dict.keys():
            self.stats_dict[k] = self.lux_context.statistics(k)
        
        self.stats_string = ' | '.join(['%s'%self.stats_format[k](v) for k,v in self.stats_dict.items()])
              
class LuxFilmDisplay(LuxTimerThread):
    '''
    Periodically update render result with Lux's framebuffer
    '''
    RE = None
            
    def start(self, RE):
        self.RE = RE
        LuxTimerThread.start(self)
            
    def kick(self, render_end=False):
        if self.RE is not None:
            px = [] #self.lux_context.framebuffer()
            xres = int(self.lux_context.statistics('filmXres'))
            yres = int(self.lux_context.statistics('filmYres'))
            time = self.lux_context.statistics('secElapsed')
            if render_end:
                LuxLog('Final render result %ix%i' % (xres,yres))
            else:
                LuxLog('Updating render result %ix%i' % (xres,yres))
            self.RE.update_framebuffer(xres,yres,px)

class LuxManager(LuxOutput):
    '''
    Use the pylux API.
    
    Instances of this class will represent a Lux rendering context
    '''
    
    # Give each context a unique serial number
    context_count = 0
    @staticmethod
    def get_context_number():
        LuxManager.context_count += 1
        return LuxManager.context_count
    
    lux_context     = None
    
    stats_thread    = None
    fb_thread       = None
    started         = True
    
    def __init__(self, manager_name = '', api_type='FILE'):
        if api_type == 'FILE':
            lux = luxrender.module.file_api.luxrender.pylux
        elif api_type == 'API':
            lux = luxrender.module.pure_api.luxrender.pylux
        
        if manager_name is not '': manager_name = ' (%s)' % manager_name
        self.lux_context = lux.Context('LuxContext %04i%s' % (LuxManager.get_context_number(), manager_name))
        
        self.reset()

    def start(self, RE):
        if self.started:
            LuxLog('Already rendering!')
            return
        
        self.lux_context.worldEnd()
        
        self.stats_thread.start()
        self.fb_thread.start(RE)
        self.started = True
    
    def reset(self):
        if self.stats_thread is not None and self.stats_thread.isAlive():
            self.stats_thread.stop()
            self.stats_thread.join()
        
        self.stats_thread  = LuxAPIStats(self.lux_context)
        
        if not self.started: return
        self.started = False
        
        self.lux_context.exit()
        self.lux_context.wait()
        
        # Get the last image
        if self.fb_thread is not None and self.fb_thread.isAlive():
            self.fb_thread.stop()
            self.fb_thread.join()
            # Get last FB
            self.fb_thread.kick(render_end=True)
        
        self.fb_thread  = LuxFilmDisplay(self.lux_context)
        
        self.lux_context.cleanup()
        
    def __del__(self):
        '''
        Gracefully exit() lux upon destruction
        '''
        self.reset()
