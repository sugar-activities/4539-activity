#!/usr/bin/env python
# -*- coding: UTF-8 -*-

""" 
    Simple Function graph Plotter
    © Thomas Führinger, Sam Tygier 2005-2007
    http://lybniz2.sourceforge.net/
    
    Version 1.3.2
    Requires PyGtk 2.6
    Released under the terms of the revised BSD license
    Modified: 2007-12-14
    
    Sugarization by Daniel Francis
"""

from __future__ import division
import gtk, pango
import sys
import math
from math import *
from sugar.activity import activity
try:
    from sugar.graphics.toolbarbox import ToolbarBox
    from sugar.activity.widgets import StopButton, ActivityToolbarButton, ToolbarButton
    have_toolbox = True
except ImportError:
    have_toolbox = False
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.toggletoolbutton import ToggleToolButton
from sugar.graphics.radiotoolbutton import RadioToolButton
from gettext import gettext as _

connect_points = True
x_res = 1
y1 = "sin(x)"
y2 = ""
y3 = ""
x_max = "5.0"
x_min = "-5.0"
x_scale = "1.0"
y_max = "3.0"
y_min = "-3.0"
y_scale = "1.0"

enable_profiling = False
if enable_profiling:
    from time import time

# create a safe namespace for the eval()s in the graph drawing code
def sub_dict(somedict, somekeys, default=None):
	return dict([ (k, somedict.get(k, default)) for k in somekeys ])
# a list of the functions from math that we want.
safe_list = ['math','acos', 'asin', 'atan', 'atan2', 'ceil', 'cos', 'cosh', 'degrees', 'e', 'exp', 'fabs', 'floor', 'fmod', 'frexp', 'hypot', 'ldexp', 'log', 'log10', 'modf', 'pi', 'pow', 'radians', 'sin', 'sinh', 'sqrt', 'tan', 'tanh','fac','sinc']
safe_dict = sub_dict(locals(), safe_list)

#add any needed builtins back in.
safe_dict['abs'] = abs

def marks(min_val,max_val,minor=1):
    "yield positions of scale marks between min and max. For making minor marks, set minor to the number of minors you want between majors"
    try:
        min_val = float(min_val)
        max_val = float(max_val)
    except:
        print "needs 2 numbers"
        raise ValueError

    if(min_val >= max_val):
        print "min bigger or equal to max"
        raise ValueError		

    a = 0.2 # tweakable control for when to switch scales
            # big a value results in more marks

    a = a + log10(minor)

    width = max_val - min_val
    log10_range = log10(width)

    interval = 10 ** int(floor(log10_range - a))
    lower_mark = min_val - fmod(min_val,interval)

    if lower_mark < min_val:
        lower_mark += interval

    a_mark = lower_mark
    while a_mark <= max_val:
        if abs(a_mark) < interval / 2:
            a_mark = 0
        yield a_mark
        a_mark += interval

class GraphClass:
    def __init__(self, parent):
        self.parent = parent
        self.prev_y = [None, None, None]
        self.selection = [[None, None], [None, None]]
        self.drawing_area = gtk.DrawingArea()
        self.drawing_area.set_events(gtk.gdk.EXPOSURE_MASK | gtk.gdk.LEAVE_NOTIFY_MASK | gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK | gtk.gdk.POINTER_MOTION_MASK |gtk.gdk.POINTER_MOTION_HINT_MASK)
        self.scale_style = "dec"
        self.drawing_area.connect("expose_event", self.expose_event)
        self.drawing_area.connect("configure_event", self.configure_event)
        self.drawing_area.connect("button_press_event", self.button_press_event)
        self.drawing_area.connect("button_release_event", self.button_release_event)
        self.drawing_area.connect("motion_notify_event", self.motion_notify_event)
    
    def button_press_event(self, widget, event):
        global x_sel, y_sel
        if event.button == 1:
            self.selection[0][0], self.selection[0][1] = int(event.x), int(event.y)
            self.selection[1][0], self.selection[1][1] = None, None

    # End of selection
    def button_release_event(self, widget, event):
        if event.button == 1 and event.x != self.selection[0][0] and event.y != self.selection[0][1]:
            xmi, ymi = min(self.graph_x(self.selection[0][0]), self.graph_x(event.x)), min(self.graph_y(self.selection[0][1]), self.graph_y(event.y))
            xma, yma = max(self.graph_x(self.selection[0][0]), self.graph_x(event.x)), max(self.graph_y(self.selection[0][1]), self.graph_y(event.y))
            self.x_min, self.y_min, self.x_max, self.y_max = xmi, ymi, xma, yma
            self.parent.parameter_entries_repopulate()
            self.plot()
            self.selection[1][0] = None
            self.selection[0][0] = None

    # Draw rectangle during mouse movement
    def motion_notify_event(self, widget, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        if state & gtk.gdk.BUTTON1_MASK and self.selection[0][0] is not None:
            gc = self.drawing_area.get_style().black_gc
            gc.set_function(gtk.gdk.INVERT)
            if self.selection[1][0] is not None:
                x0 = min(self.selection[1][0], self.selection[0][0])
                y0 = min(self.selection[1][1], self.selection[0][1])
                w = abs(self.selection[1][0] - self.selection[0][0])
                h = abs(self.selection[1][1] - self.selection[0][1])
                self.pix_map.draw_rectangle(gc, False, x0, y0, w, h)
            x0 = min(self.selection[0][0], int(x))
            y0 = min(self.selection[0][1], int(y))
            w = abs(int(x) - self.selection[0][0])
            h = abs(int(y) - self.selection[0][1])
            self.pix_map.draw_rectangle(gc, False, x0, y0, w, h)
            self.selection[1][0], self.selection[1][1] = int(x), int(y)
            self.draw_drawable()
    
    def draw_drawable(self):
        x, y, w, h = self.drawing_area.get_allocation()
        self.drawing_area.window.draw_drawable(self.drawing_area.get_style().fg_gc[gtk.STATE_NORMAL], self.pix_map, 0, 0, 0, 0, w, h)

    def graph_x(self, x):
        "Calculate position on graph from point on canvas"
        return x  * (self.x_max - self.x_min) / self.canvas_width + self.x_min

    def graph_y(self, y):
        return self.y_max - (y * (self.y_max - self.y_min) / self.canvas_height)
    
    def plot(self):
        self.pix_map.draw_rectangle(self.drawing_area.get_style().white_gc, True, 0, 0, self.canvas_width, self.canvas_height)

        if (self.scale_style == "cust"):

            #draw cross
            self.pix_map.draw_lines(self.gc['black'], [(int(round(self.canvas_x(0))),0),(int(round(self.canvas_x(0))),self.canvas_height)])
            self.pix_map.draw_lines(self.gc['black'], [(0,int(round(self.canvas_y(0)))),(self.canvas_width,int(round(self.canvas_y(0))))])
            # old style axis marks
            iv = self.x_scale * self.canvas_width / (self.x_max - self.x_min) # pixel interval between marks
            os = self.canvas_x(0) % iv # pixel offset of first mark 
            # loop over each mark.
            for i in xrange(int(self.canvas_width / iv + 1)):
                #multiples of iv, cause adding of any error in iv, so keep iv as float
                # use round(), to get to closest pixel, int() to prevent warning
                self.pix_map.draw_lines(self.gc['black'], [(int(round(os + i * iv)), int(round(self.canvas_y(0) - 5))), (int(round(os + i * iv)), int(round(self.canvas_y(0) + 5)))])
            
            # and the y-axis
            iv = self.y_scale * self.canvas_height / (self.y_max - self.y_min)
            os = self.canvas_y(0) % iv
            for i in xrange(int(self.canvas_height / iv + 1)):
                self.pix_map.draw_lines(self.gc['black'], [(int(round(self.canvas_x(0) - 5)), int(round(i * iv + os))), (int(round(self.canvas_x(0) + 5)), int(round(i * iv + os)))])			
        
        else:
            #new style
            factor = 1
            if (self.scale_style == "rad"): factor = pi

            # where to put the numbers
            numbers_x_pos = -10
            numbers_y_pos = 10
            
            # where to center the axis
            center_x_pix = int(round(self.canvas_x(0)))
            center_y_pix = int(round(self.canvas_y(0)))			
            if (center_x_pix < 5): center_x_pix = 5
            if (center_x_pix < 20):numbers_x_pos = 10
            if (center_y_pix < 5): center_y_pix = 5
            if (center_x_pix > self.canvas_width - 5): center_x_pix = self.canvas_width - 5
            if (center_y_pix > self.canvas_height -5): center_y_pix = self.canvas_height - 5;
            if (center_y_pix > self.canvas_height -20): numbers_y_pos = - 10
            
            # draw cross
            self.pix_map.draw_lines(self.gc['black'], [(center_x_pix,0),(center_x_pix,self.canvas_height)])
            self.pix_map.draw_lines(self.gc['black'], [(0,center_y_pix),(self.canvas_width,center_y_pix)])

            for i in marks(self.x_min / factor, self.x_max / factor):
                label = '%g' % i
                if (self.scale_style == "rad"): label += '\xCF\x80'
                i = i * factor

                self.pix_map.draw_lines(self.gc['black'], [(int(round(self.canvas_x(i))), center_y_pix - 5), (int(round(self.canvas_x(i))), center_y_pix + 5)])

                self.layout.set_text(label)
                extents = self.layout.get_pixel_extents()[1]
                if (numbers_y_pos < 0): adjust = extents[3]
                else: adjust = 0
                self.pix_map.draw_layout(self.gc['black'],int(round(self.canvas_x(i))), center_y_pix + numbers_y_pos - adjust,self.layout)

            for i in marks(self.y_min,self.y_max):
                label = '%g' % i

                self.pix_map.draw_lines(self.gc['black'], [(center_x_pix - 5, int(round(self.canvas_y(i)))), (center_x_pix + 5, int(round(self.canvas_y(i))))])

                self.layout.set_text(label)
                extents = self.layout.get_pixel_extents()[1]
                if (numbers_x_pos < 0): adjust = extents[2]
                else: adjust = 0
                self.pix_map.draw_layout(self.gc['black'],center_x_pix +numbers_x_pos - adjust,int(round(self.canvas_y(i))),self.layout)

            # minor marks
            for i in marks(self.x_min / factor, self.x_max / factor, minor=10):
                i = i * factor
                self.pix_map.draw_lines(self.gc['black'], [(int(round(self.canvas_x(i))), center_y_pix - 2), (int(round(self.canvas_x(i))), center_y_pix +2)])

            for i in marks(self.y_min, self.y_max, minor=10):
                label = '%g' % i
                self.pix_map.draw_lines(self.gc['black'], [(center_x_pix - 2, int(round(self.canvas_y(i)))), (center_x_pix +2, int(round(self.canvas_y(i))))])

        plots = []
        # precompile the functions
        try:
            compiled_y1 = compile(y1.replace("^","**"),"",'eval')
            plots.append((compiled_y1,0,self.gc['blue']))
        except:
            compiled_y1 = None
        try:
            compiled_y2 = compile(y2.replace("^","**"),"",'eval')
            plots.append((compiled_y2,1,self.gc['red']))
        except:
            compiled_y2 = None
        try:
            compiled_y3 = compile(y3.replace("^","**"),"",'eval')
            plots.append((compiled_y3,2,self.gc['green']))
        except:
            compiled_y3 = None

        self.prev_y = [None, None, None]

        if enable_profiling:
            start_graph = time()

        if len(plots) != 0:
            for i in xrange(0,self.canvas_width,x_res):
                x = self.graph_x(i + 1)
                for e in plots:
                    safe_dict['x']=x
                    try:
                        y = eval(e[0],{"__builtins__":{}},safe_dict)
                        y_c = int(round(self.canvas_y(y)))

                        if y_c < 0 or y_c > self.canvas_height:
                            raise ValueError

                        if connect_points and self.prev_y[e[1]] is not None:
                            self.pix_map.draw_lines(e[2], [(i, self.prev_y[e[1]]), (i + x_res, y_c)])
                        else:
                            self.pix_map.draw_points(e[2], [(i + x_res, y_c)])
                        self.prev_y[e[1]] = y_c
                    except Exception, exc:
                        print exc
                        #print "Error at %d: %s" % (x, sys.exc_value)
                        self.prev_y[e[1]] = None

        if enable_profiling:
            print "time to draw graph:", (time() - start_graph) * 1000, "ms"

        self.draw_drawable()
    
    def configure_event(self, widget, event):
        x, y, w, h = widget.get_allocation()
        self.pix_map = gtk.gdk.Pixmap(widget.window, w, h)
        
        # make colors
        self.gc = dict()
        for name, color in (('black',(0,0,0)),('red',(32000,0,0)),('blue',(0,0,32000)),('green',(0,32000,0))):
            self.gc[name] =self.pix_map.new_gc()
            self.gc[name].set_rgb_fg_color(gtk.gdk.Color(red=color[0],green=color[1],blue=color[2]))
        self.layout = pango.Layout(widget.create_pango_context())
        self.canvas_width = w
        self.canvas_height = h
        self.x_max = eval(x_max,{"__builtins__":{}},safe_dict)
        self.x_min = eval(x_min,{"__builtins__":{}},safe_dict)
        self.x_scale = eval(x_scale,{"__builtins__":{}},safe_dict)
        self.y_max = eval(y_max,{"__builtins__":{}},safe_dict)
        self.y_min = eval(y_min,{"__builtins__":{}},safe_dict)
        self.y_scale = eval(y_scale,{"__builtins__":{}},safe_dict)
        self.plot()
        return True
    
    def expose_event(self, widget, event):
        x, y, w, h = event.area
        widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL], self.pix_map, x, y, x, y, w, h)
        return False
    
    def canvas_y(self, y):
        return (self.y_max - y) * self.canvas_height / (self.y_max - self.y_min)

    def canvas_x(self, x):
        "Calculate position on canvas to point on graph"
        return (x - self.x_min) * self.canvas_width / (self.x_max - self.x_min)

class LybnizActivity(activity.Activity):
    def write_file(self, file_path):
        x, y, w, h = self.graph.drawing_area.get_allocation()
        pix_buffer = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, False, 8, w, h)
        pix_buffer.get_from_drawable(self.graph.pix_map, self.graph.pix_map.get_colormap(), 0, 0, 0, 0, w, h)
        pix_buffer.save(file_path, "png")
    
    def parameter_entries_repopulate(self):
        # set text in entries for parameters
        self.y1_entry.set_text(y1)
        self.y2_entry.set_text(y2)
        self.y3_entry.set_text(y3)
        self.x_min_entry.set_text(str(self.graph.x_min))
        self.x_max_entry.set_text(str(self.graph.x_max))
        self.x_scale_entry.set_text(str(self.graph.x_scale))
        self.y_min_entry.set_text(str(self.graph.y_min))
        self.y_max_entry.set_text(str(self.graph.y_max))
        self.y_scale_entry.set_text(str(self.graph.y_scale))

    def zoom_in(self, widget, event=None):
        "Narrow the plotted section by half"
        center_x = (self.graph.x_min + self.graph.x_max) / 2
        center_y = (self.graph.y_min + self.graph.y_max) / 2
        range_x = (self.graph.x_max - self.graph.x_min)
        range_y = (self.graph.y_max - self.graph.y_min)

        self.graph.x_min = center_x - (range_x / 4)
        self.graph.x_max = center_x + (range_x / 4)
        self.graph.y_min = center_y - (range_y / 4)
        self.graph.y_max = center_y +(range_y / 4)

        self.parameter_entries_repopulate()
        self.graph.plot()

    def zoom_out(self, widget, event=None):
        "Double the plotted section"
        center_x = (self.graph.x_min + self.graph.x_max) / 2
        center_y = (self.graph.y_min + self.graph.y_max) / 2
        range_x = (self.graph.x_max - self.graph.x_min)
        range_y = (self.graph.y_max - self.graph.y_min)

        self.graph.x_min = center_x - (range_x)
        self.graph.x_max = center_x + (range_x)
        self.graph.y_min = center_y - (range_y)
        self.graph.y_max = center_y +(range_y)	

        self.parameter_entries_repopulate()
        self.graph.plot()

    def zoom_reset(self, widget, event=None):
        "Set the range back to the user's input"

        self.graph.x_min = eval(x_min,{"__builtins__":{}},safe_dict)
        self.graph.y_min = eval(y_min,{"__builtins__":{}},safe_dict)
        self.graph.x_max = eval(x_max,{"__builtins__":{}},safe_dict)
        self.graph.y_max = eval(y_max,{"__builtins__":{}},safe_dict)
        self.x_min_entry.set_text(self.x_min)
        self.x_max_entry.set_text(self.x_max)
        self.x_scale_entry.set_text(self.x_scale)
        self.y_min_entry.set_text(self.y_min)
        self.y_max_entry.set_text(self.y_max)
        self.y_scale_entry.set_text(self.y_scale)
        self.graph.plot()

    def evaluate(self, widget, event=None):
        "Evaluate a given x for the three functions"

        def entry_changed(widget):
            for e in ((y1, dlg_win.y1_entry), (y2, dlg_win.y2_entry), (y3, dlg_win.y3_entry)):
                try:
                    x = float(dlg_win.x_entry.get_text())
                    safe_dict['x']=x
                    e[1].set_text(str(eval(e[0].replace("^","**"),{"__builtins__":{}},safe_dict)))
                except:
                    if len(e[0]) > 0:
                        e[1].set_text("Error: %s" % sys.exc_value)
                    else:
                        e[1].set_text("")

        def close(self):
            dlg_win.destroy()

        dlg_win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        dlg_win.set_position(gtk.WIN_POS_CENTER)
        dlg_win.set_title(_("Evaluate"))
        dlg_win.connect("destroy", close)

        dlg_win.x_entry = gtk.Entry()
        dlg_win.x_entry.set_editable(True)
        dlg_win.x_entry.connect("changed", entry_changed)
        dlg_win.y1_entry = gtk.Entry()
        dlg_win.y1_entry.set_size_request(200, 24)
        dlg_win.y1_entry.set_sensitive(False)
        dlg_win.y2_entry = gtk.Entry()
        dlg_win.y2_entry.set_size_request(200, 24)
        dlg_win.y2_entry.set_sensitive(False)
        dlg_win.y3_entry = gtk.Entry()
        dlg_win.y3_entry.set_size_request(200, 24)
        dlg_win.y3_entry.set_sensitive(False)

        table = gtk.Table(2, 5)
        label = gtk.Label("x = ")
        label.set_alignment(0, .5)
        table.attach(label, 0, 1, 0, 1, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        table.attach(dlg_win.x_entry, 1, 2, 0, 1)
        label = gtk.Label("y1 = ")
        label.set_alignment(0, .5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("blue"))
        table.attach(label, 0, 1, 1, 2, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        table.attach(dlg_win.y1_entry, 1, 2, 1, 2)
        label = gtk.Label("y2 = ")
        label.set_alignment(0, .5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
        table.attach(label, 0, 1, 2, 3, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        table.attach(dlg_win.y2_entry, 1, 2, 2, 3)
        label = gtk.Label("y3 = ")
        label.set_alignment(0, .5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("DarkGreen"))
        table.attach(label, 0, 1, 3, 4, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        table.attach(dlg_win.y3_entry, 1, 2, 3, 4)
        table.set_border_width(24)
        dlg_win.add(table)
        dlg_win.show_all()
    
    def plot(self, widget, event=None):
        global x_max, x_min, x_scale, y_max, y_min, y_scale, y1, y2, y3
        x_max = self.x_max_entry.get_text()
        x_min = self.x_min_entry.get_text()
        x_scale = self.x_scale_entry.get_text()

        y_max = self.y_max_entry.get_text()
        y_min = self.y_min_entry.get_text()
        y_scale = self.y_scale_entry.get_text()

        self.graph.x_max = eval(x_max,{"__builtins__":{}},safe_dict)
        self.graph.x_min = eval(x_min,{"__builtins__":{}},safe_dict)
        self.graph.x_scale = eval(x_scale,{"__builtins__":{}},safe_dict)

        self.graph.y_max = eval(y_max,{"__builtins__":{}},safe_dict)
        self.graph.y_min = eval(y_min,{"__builtins__":{}},safe_dict)
        self.graph.y_scale = eval(y_scale,{"__builtins__":{}},safe_dict)

        y1 = self.y1_entry.get_text()
        y2 = self.y2_entry.get_text()
        y3 = self.y3_entry.get_text()

        self.graph.plot()

    def toggle_connect(self, widget, event=None):
        "Toggle between a graph that connects points with lines and one that does not"
        global connect_points
        connect_points = not connect_points
        self.graph.plot()
    
    def scale_dec(self, widget, event=None):
        self.graph.scale_style = "dec"
        self.scale_box.hide()
        self.plot(None)


    def scale_rad(self, widget, event=None):
        self.graph.scale_style = "rad"
        self.scale_box.hide()
        self.plot(None)

    def scale_cust(self, widget, event=None):
        self.graph.scale_style = "cust"
        self.scale_box.show()
        self.plot(None)

    def __init__(self, handle):
        activity.Activity.__init__(self, handle)
        self.y1 = y1
        self.y2 = y2
        self.y3 = y3
        self.x_max = x_max
        self.x_min = x_min
        self.x_scale = x_scale
        self.y_max = y_max
        self.y_min = y_min
        self.y_scale = y_scale
        if have_toolbox:
            self.toolbar_box = ToolbarBox()
            self.activity_button = ActivityToolbarButton(self)
            self.activity_button.page.share.hide()
            self.toolbar_box.toolbar.insert(self.activity_button, 0)
            self.activity_button.show()
            self.graph_item = ToolbarButton()
            self.graph_item.props.icon_name = 'graph'
        else:
            self.toolbox = activity.ActivityToolbox(self)
            activity_toolbar = self.toolbox.get_activity_toolbar()
            activity_toolbar.share.props.visible = False
        self.graph_toolbar = gtk.Toolbar()
        if have_toolbox:
            self.graph_item.props.page = self.graph_toolbar
        else:
            self.toolbox.add_toolbar(_('Graph'), self.graph_toolbar)
        self.plot_item = ToolButton('gtk-refresh')
        self.plot_item.props.tooltip = _("Plot")
        self.plot_item.connect("clicked", self.plot)
        self.plot_item.show()
        self.graph_toolbar.insert(self.plot_item, 0)
        self.evaluate_item = ToolButton('evaluate')
        self.evaluate_item.props.tooltip = _('Evaluate')
        self.evaluate_item.connect("clicked", self.evaluate)
        self.evaluate_item.show()
        self.graph_toolbar.insert(self.evaluate_item, -1)
        separator = gtk.SeparatorToolItem()
        separator.show()
        self.graph_toolbar.insert(separator, -1)
        self.zoom_in_item = ToolButton('zoom-in')
        self.zoom_in_item.props.tooltip = _('Zoom In')
        self.zoom_in_item.connect("clicked", self.zoom_in)
        self.zoom_in_item.show()
        self.graph_toolbar.insert(self.zoom_in_item, -1)
        self.zoom_out_item = ToolButton('zoom-out')
        self.zoom_out_item.props.tooltip = _('Zoom Out')
        self.zoom_out_item.connect("clicked", self.zoom_out)
        self.zoom_out_item.show()
        self.graph_toolbar.insert(self.zoom_out_item, -1)
        self.zoom_reset_item = ToolButton('zoom-original')
        self.zoom_reset_item.props.tooltip = _('Zoom Reset')
        self.zoom_reset_item.connect("clicked", self.zoom_reset)
        self.zoom_reset_item.show()
        self.graph_toolbar.insert(self.zoom_reset_item, -1)
        separator = gtk.SeparatorToolItem()
        separator.show()
        self.graph_toolbar.insert(separator, -1)
        self.connect_points_item = ToggleToolButton('connect-points')
        self.connect_points_item.set_tooltip(_("Connect Points"))
        self.connect_points_item.set_active(True)
        self.connect_points_item.connect("toggled", self.toggle_connect)
        self.connect_points_item.show()
        self.graph_toolbar.insert(self.connect_points_item, -1)
        separator = gtk.SeparatorToolItem()
        separator.show()
        self.graph_toolbar.insert(separator, -1)
        self.decimal_item = RadioToolButton()
        self.decimal_item.set_named_icon('decimal')
        self.decimal_item.set_tooltip(_("Decimal Scale Style"))
        self.decimal_item.connect("toggled", self.scale_dec)
        self.decimal_item.show()
        self.graph_toolbar.insert(self.decimal_item, -1)
        self.radians_item = RadioToolButton()
        self.radians_item.set_named_icon('radian')
        self.radians_item.set_tooltip(_("Radians Scale Style"))
        self.radians_item.set_group(self.decimal_item)
        self.radians_item.connect("toggled", self.scale_rad)
        self.radians_item.show()
        self.graph_toolbar.insert(self.radians_item, -1)
        self.custom_item = RadioToolButton()
        self.custom_item.set_named_icon('custom')
        self.custom_item.set_tooltip(_("Custom Scale Style"))
        self.custom_item.set_group(self.radians_item)
        self.custom_item.connect("toggled", self.scale_cust)
        self.custom_item.show()
        self.graph_toolbar.insert(self.custom_item, -1)
        self.graph_toolbar.show()
        if have_toolbox:
            self.graph_item.show()
            self.toolbar_box.toolbar.insert(self.graph_item, -1)
            separator = gtk.SeparatorToolItem()
            separator.set_draw(False)
            separator.set_expand(True)
            separator.show()
            self.toolbar_box.toolbar.insert(separator, -1)
            self.stop = StopButton(self)
            self.stop.show()
            self.toolbar_box.toolbar.insert(self.stop, -1)
            self.set_toolbar_box(self.toolbar_box)
            self.toolbar_box.show()
        else:
            self.toolbox.show()
            self.set_toolbox(self.toolbox)
        self.v_box = gtk.VBox()
        self.set_canvas(self.v_box)
        self.parameter_entries = gtk.Table(6, 3)
        self.y1_entry = gtk.Entry()
        self.y2_entry = gtk.Entry()
        self.y3_entry = gtk.Entry()
        self.x_min_entry = gtk.Entry()
        self.x_min_entry.set_size_request(90, 24)
        self.x_min_entry.set_alignment(1)
        self.x_max_entry = gtk.Entry()
        self.x_max_entry.set_size_request(90, 24)
        self.x_max_entry.set_alignment(1)
        self.x_scale_entry = gtk.Entry()
        self.x_scale_entry.set_size_request(90, 24)
        self.x_scale_entry.set_alignment(1)
        self.y_min_entry = gtk.Entry()
        self.y_min_entry.set_size_request(90, 24)
        self.y_min_entry.set_alignment(1)
        self.y_max_entry = gtk.Entry()
        self.y_max_entry.set_size_request(90, 24)
        self.y_max_entry.set_alignment(1)
        self.y_scale_entry = gtk.Entry()
        self.y_scale_entry.set_size_request(90, 24)
        self.y_scale_entry.set_alignment(1)
        self.y1_entry.set_text(self.y1)
        self.y2_entry.set_text(self.y2)
        self.y3_entry.set_text(self.y3)
        self.x_min_entry.set_text(self.x_min)
        self.x_max_entry.set_text(self.x_max)
        self.x_scale_entry.set_text(self.x_scale)
        self.y_min_entry.set_text(self.y_min)
        self.y_max_entry.set_text(self.y_max)
        self.y_scale_entry.set_text(self.y_scale)
        self.scale_box = gtk.HBox()
        label = gtk.Label("y1 = ")
        label.set_alignment(0, .5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("blue"))
        self.parameter_entries.attach(label, 0, 1, 0, 1, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.y1_entry, 1, 2, 0, 1)
        label = gtk.Label(_("X min"))
        label.set_alignment(1, .5)
        self.parameter_entries.attach(label, 2, 3, 0, 1, xpadding=5, ypadding=7, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.x_min_entry, 3, 4, 0, 1, xoptions=gtk.FILL)
        label = gtk.Label(_("Y min"))
        label.set_alignment(1, .5)
        self.parameter_entries.attach(label, 4, 5, 0, 1, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.y_min_entry, 5, 6, 0, 1, xpadding=5, xoptions=gtk.FILL)
        label = gtk.Label("y2 = ")
        label.set_alignment(0, .5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("red"))
        self.parameter_entries.attach(label, 0, 1, 1, 2, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.y2_entry, 1, 2, 1, 2)
        label = gtk.Label(_("X max"))
        label.set_alignment(1, .5)
        self.parameter_entries.attach(label, 2, 3, 1, 2, xpadding=5, ypadding=7, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.x_max_entry, 3, 4, 1, 2, xoptions=gtk.FILL)
        label = gtk.Label(_("Y max"))
        label.set_alignment(1, .5)
        self.parameter_entries.attach(label, 4, 5, 1, 2, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.y_max_entry, 5, 6, 1, 2, xpadding=5, xoptions=gtk.FILL)
        label = gtk.Label("y3 = ")
        label.set_alignment(0, .5)
        label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("DarkGreen"))
        self.parameter_entries.attach(label, 0, 1, 2, 3, xpadding=5, ypadding=5, xoptions=gtk.FILL)
        self.parameter_entries.attach(self.y3_entry, 1, 2, 2, 3)
        label = gtk.Label(_("X scale"))
        label.set_alignment(0, .5)
        self.scale_box.add(label)
        self.scale_box.add(self.x_scale_entry)
        label = gtk.Label(_("Y scale"))
        label.set_alignment(0, .5)
        self.scale_box.add(label)
        self.scale_box.add(self.y_scale_entry)
        self.parameter_entries.attach(self.scale_box, 2, 6, 2, 3, xpadding=5, xoptions=gtk.FILL)
        self.v_box.pack_start(self.parameter_entries, False, True, 4)
        self.parameter_entries.show_all()
        self.graph = GraphClass(self)
        self.v_box.pack_start(self.graph.drawing_area, True, True, 0)
        self.status_bar = gtk.Statusbar()
        self.status_bar.ContextId = self.status_bar.get_context_id("Dummy")
        self.status_bar.show()
        self.v_box.pack_end(self.status_bar, False, True, 0)
        self.v_box.show_all()
