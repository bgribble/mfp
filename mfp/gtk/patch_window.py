
import clutter 

from text_element import TextElement
from processor_element import ProcessorElement, ConnectionElement 

MOD_SHIFT = 50
MOD_RSHIFT = 62
MOD_CTRL = 66
MOD_ALT = 64
MOD_WIN = 133
MOD_ESC = 9 
KEY_TAB = 65289 
KEY_BKSP = 65288
KEY_PGUP = 65365
KEY_PGDN = 65366
KEY_HOME = 65360
KEY_END = 65367
KEY_INS = 65379
KEY_DEL = 65535
KEY_UP = 65362
KEY_DN = 65364
KEY_LEFT = 65361
KEY_RIGHT = 65363
KEY_ENTER = 65293 

from mfp.gui import MFPGUI 

class PatchWindow(object):

	def __init__(self):
		self.stage = clutter.Stage()
		
		self.mouse_buttons = set()
		self.mod_keys = set()
		self.mod_esc = False 
		self.pointer_x = None
		self.pointer_y = None

		self.color_unselected = clutter.color_from_string('Black')
		self.color_selected = clutter.color_from_string('Red')

		self.objects = [] 
		self.selected = None

		# used while building a connection
		self.conn_mode = None 
		self.conn_start_obj = None
		self.conn_start_port = None
		self.conn_end_obj = None
		self.conn_end_port = None

		# configure clutter stage 
		self.stage.set_size(320, 240)
		self.stage.set_title("MFP")
		
		self.stage.connect('button-press-event', self.mouse_down_cb)
		self.stage.connect('button-release-event', self.mouse_up_cb)
		self.stage.connect('key-press-event', self.key_down_cb)
		self.stage.connect('key-release-event', self.key_up_cb)
		self.stage.connect('motion-event', self.mouse_motion_cb)
		self.stage.connect('destroy', self.quit)

		# leave event: handler should figure out what is being left and 
		# clear modifier keys if the main window is being left 
		#self.stage.connect('leave-event', self.leave_cb)

		self.stage.show_all()

	def add_processor(self):
		b = ProcessorElement(self, self.pointer_x, self.pointer_y)
		self.objects.append(b)
		self.select(b)
		b.toggle_edit()

	def add_text(self):
		b = TextElement(self, self.pointer_x, self.pointer_y)
		self.objects.append(b)
		self.select(b)
		b.toggle_edit()

	def select(self, obj):
		if self.conn_mode == 'c':
			self.conn_end_obj = obj
		elif self.conn_mode == 'C':
			self.conn_start_obj = obj

		if self.selected is not obj and self.selected is not None:
			self.selected.unselect()
		obj.select()
		self.selected = obj
	
	def select_next(self):
		if self.selected is None and len(self.objects) > 0:
			self.select(self.objects[0])
		cur_ind = self.objects.index(self.selected)
		self.select(self.objects[(cur_ind+1) % len(self.objects)])

	def select_prev(self):
		if self.selected is None and len(self.objects) > 0:
			self.select(self.objects[-1])
		cur_ind = self.objects.index(self.selected)
		self.select(self.objects[cur_ind-1])

	def dispatch_key(self, key):
		# should handle this with a dict of keysym to handler 
		# with contexts (modes) 

		# global functions 
		if key == 'C-q':
			self.quit()
		elif key == 'C-s':
			self.save()

		# creating elements 
		elif key == 'C-a':
			self.add_processor()
		elif key == 'C-t':
			self.add_text()

		# selection/editing 
		elif key == 'C-u':
			if self.selected:
				self.selected.unselect()
				self.selected = None
		elif key == 'S-C-u':
			if self.selected:
				self.selected.toggle_edit()
		elif key == 'TAB':
			self.select_next()
		elif key == 'S-TAB':
			self.select_prev()

		# connections 
		elif key == 'c':
			if self.selected:
				self.conn_mode = 'c'
				self.conn_start_obj = self.selected 
				self.conn_end_obj = None
				self.conn_start_port = 0
				self.conn_end_port = 0
		elif key == 'S-c':
			if self.selected:
				self.conn_mode = 'C'
				self.conn_start_obj = None
				self.conn_end_obj = self.selected
				self.conn_start_port = 0
				self.conn_end_port = 0

		elif key in ('1', '2', '3', '4', '5', '6', '7', '8', '9'):
			if self.conn_mode == 'c':
				if self.conn_end_obj is None:
					self.conn_start_port = int(key) - 1
				else:
					self.conn_end_port = int(key) - 1
			elif self.conn_mode == 'C':
				if self.conn_start_obj is None:
					self.conn_end_port = int(key) - 1
				else:
					self.conn_start_port = int(key) - 1
		elif key == 'RET':
			print self.conn_mode, self.conn_start_obj, self.conn_end_obj
			if self.conn_mode is not None:
				if self.conn_start_obj is not None and self.conn_end_obj is not None:
					print "Making connection:"
					print self.conn_start_obj, self.conn_start_port, '-->', self.conn_end_obj, self.conn_end_port
		
					if MFPGUI.connect(self.conn_start_obj.proc_id, self.conn_start_port,
					                  self.conn_end_obj.proc_id, self.conn_end_port):
						c = ConnectionElement(self, self.conn_start_obj, self.conn_start_port,
											  self.conn_end_obj, self.conn_end_port)
						self.conn_start_obj.connections_out.append(c)
						self.conn_end_obj.connections_in.append(c)
					else:
						print "Cannot make connection"

					self.conn_mode = None 
		# movement 
		elif key == 'UP':
			self.move_selected(0, -1)	
		elif key == 'DOWN':
			self.move_selected(0, 1)
		elif key == 'LEFT':
			self.move_selected(-1, 0)	
		elif key == 'RIGHT':
			self.move_selected(1, 0)
		elif key == 'S-UP':
			self.move_selected(0, -5)	
		elif key == 'S-DOWN':
			self.move_selected(0, 5)
		elif key == 'S-LEFT':
			self.move_selected(-5, 0)	
		elif key == 'S-RIGHT':
			self.move_selected(5, 0)
		elif key == 'C-UP':
			self.move_selected(0, -25)	
		elif key == 'C-DOWN':
			self.move_selected(0, 25)
		elif key == 'C-LEFT':
			self.move_selected(-25, 0)	
		elif key == 'C-RIGHT':
			self.move_selected(25, 0)

	def move_selected(self, dx, dy):
		if self.selected is None:
			return
		self.selected.move(max(0, self.selected.position_x + dx),
					       max(0, self.selected.position_y + dy))

	def mouse_motion_cb(self, stage, event):
		self.pointer_x = event.x
		self.pointer_y = event.y
		if self.selected and (1 in self.mouse_buttons):
			self.selected.drag(event.x, event.y)

	def mouse_down_cb(self, stage, event):
		self.mouse_buttons.add(1)
		if self.selected:
			self.selected.drag_start(event.x, event.y)

	def mouse_up_cb(self, stage, event):
		self.mouse_buttons.remove(1)

	def canonical_key(self, event):
		key = ''
		if self.mod_esc:
			key += 'ESC '
		if MOD_SHIFT in self.mod_keys:
			key += 'S-'
		if MOD_CTRL in self.mod_keys:
			key += 'C-'
		if MOD_ALT in self.mod_keys: 
			key += 'A-'
		if MOD_WIN in self.mod_keys:
			key += 'W-'

		ks = event.get_key_symbol()
		if ks < 256:
			key += chr(event.get_key_symbol())
		elif ks == KEY_TAB:
			key += 'TAB'
		elif ks == KEY_UP:
			key += 'UP'
		elif ks == KEY_DN:
			key += 'DOWN'
		elif ks == KEY_LEFT:
			key += 'LEFT'
		elif ks == KEY_RIGHT:
			key += 'RIGHT'
		elif ks == KEY_ENTER:
			key += 'RET'
		else:
			key += "%d" % ks
		
		return key 	

	def key_down_cb(self, stage, event):
		code = event.get_key_code()
		if code in (MOD_SHIFT, MOD_CTRL, MOD_ALT, MOD_WIN, MOD_ESC):
			self.mod_keys.add(code)
			if code == MOD_ESC:
				self.mod_esc = True
		elif code == MOD_RSHIFT:
			self.mod_keys.add(MOD_SHIFT)
		else:
			ckey = self.canonical_key(event)
			self.dispatch_key(ckey)
			print ckey
			self.mod_esc = False 

	def key_up_cb(self, stage, event):
		code = event.get_key_code()
		if code in (MOD_SHIFT, MOD_CTRL, MOD_ALT, MOD_WIN, MOD_ESC):
			try:
				self.mod_keys.remove(code)
			except KeyError:
				pass
		elif code == MOD_RSHIFT:
			self.mod_keys.remove(MOD_SHIFT)

	def quit(self, *rest):
		clutter.main_quit()


