
import clutter 

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

class PatchElement (object):
	def __init__(self, window, x, y):
		self.actor = None 
		self.stage = window
		self.position_x = x
		self.position_y = y
		self.drag_x = None
		self.drag_y = None
	
	def drag_start(self, x, y):
		self.drag_x = x - self.position_x
		self.drag_y = y - self.position_y

	def drag(self, x, y):
		self.move(x - self.drag_x, y - self.drag_y)

class ProcessorElement (PatchElement):
	def __init__(self, window, x, y):
		PatchElement.__init__(self, window, x, y)
		
		# create elements 
		self.actor = clutter.Rectangle()
		self.label = clutter.Text()
	
		# configure rectangle box 
		self.actor.set_size(50, 20)
		self.actor.set_border_width(2)
		self.actor.set_border_color(window.color_unselected)
		self.actor.set_reactive(True)

		# configure label
		self.label.set_editable(True)
		self.label.set_activatable(True)
		self.label.set_reactive(True)
		self.label.set_color(window.color_unselected) 
		self.label.connect('activate', self.text_activate_cb)

		self.move(x, y)

		# add components to stage 
		self.stage.stage.add(self.actor)
		self.stage.stage.add(self.label)
		self.stage.stage.set_key_focus(self.label)

	def text_activate_cb(self, *args):
		self.label.set_editable(False)
		self.label.set_activatable(False)
		self.stage.stage.set_key_focus(None)
		print self.label.get_text()

	def move(self, x, y):
		self.position_x = x
		self.position_y = y
		self.actor.set_position(x, y)
		self.label.set_position(x+4, y+1)

	def select(self):
		self.actor.set_border_color(self.stage.color_selected)

	def unselect(self):
		self.actor.set_border_color(self.stage.color_unselected)
	

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

		# configure clutter stage 
		self.stage.set_size(320, 240)
		self.stage.set_title("MFP")
		
		self.stage.connect('button-press-event', self.mouse_down_cb)
		self.stage.connect('button-release-event', self.mouse_up_cb)
		self.stage.connect('key-press-event', self.key_down_cb)
		self.stage.connect('key-release-event', self.key_up_cb)
		self.stage.connect('motion-event', self.mouse_motion_cb)
		#self.stage.connect('leave-event', self.leave_cb)
		self.stage.connect('destroy', self.quit)

		self.stage.show_all()

	def add_processor(self):
		b = ProcessorElement(self, self.pointer_x, self.pointer_y)
		self.objects.append(b)
		self.select(b)

	def select(self, obj):
		if self.selected is not obj and self.selected is not None:
			self.selected.unselect()
		obj.select()
		self.selected = obj
	
	def select_next(self):
		cur_ind = self.objects.index(self.selected)
		self.select(self.objects[(cur_ind+1) % len(self.objects)])

	def select_prev(self):
		cur_ind = self.objects.index(self.selected)
		self.select(self.objects[cur_ind-1])

	def dispatch_key(self, key):
		if key == 'C-q':
			self.quit()
		elif key == 'C-a':
			self.add_processor()
		elif key == 'TAB':
			self.select_next()
		elif key == 'S-TAB':
			self.select_prev()

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

	def leave_cb(self, *args): 
		print "leave callback", args
		self.mod_keys = set()
		self.mod_esc = False 

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
			print "RSHIFT"
			self.mod_keys.add(MOD_SHIFT)
		else:
			ckey = self.canonical_key(event)
			self.dispatch_key(ckey)
			print ckey
			self.mod_esc = False 

		print code, type(code), MOD_RSHIFT

	def key_up_cb(self, stage, event):
		code = event.get_key_code()
		if code in (MOD_SHIFT, MOD_CTRL, MOD_ALT, MOD_WIN, MOD_ESC):
			try:
				self.mod_keys.remove(code)
			except KeyError:
				print "up for key not active"
		elif code == MOD_RSHIFT:
			self.mod_keys.remove(MOD_SHIFT)

	def quit(self, *rest):
		clutter.main_quit()

if __name__ == "__main__":
	w = PatchWindow()
	clutter.main()

