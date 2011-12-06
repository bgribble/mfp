import clutter

black = clutter.color_from_string("Black")
white = clutter.color_from_string("White")

def subdivide(vmin, vmax, scale):
	'''
	norm = log10 of range - 1
	approx ticksize = range/approx tick count 
	closest of (1, .5, .25, .1) to normtick
	all multiples between vmin, vmax
	'''
	pts = [ vmin, vmax ]
	numpts = int(scale / self.MIN_DIV_SIZE)
	interv = (vmax-vmin)/numpts

	pts.sort()
	return pts

class ScopeActor(object):
	MARGIN_LEFT = 25
	MARGIN_BOT = 25
	MIN_DIV_SIZE = 50

	def __init__(self, stage, width, height, title):
		self.stage = stage
		self.width = width
		self.height = height
		self.title = title

		# scaling params
		self.x_min = 0
		self.x_max = 6.28 
		self.y_min = -1
		self.y_max = 1

		# initialized by create() call
		self.cl_bg = None
		self.cl_title = None
		self.cl_xaxis_bg = None
		self.cl_yaxis_bg = None
		self.cl_field = None
		self.cl_curve = None
		self.cl_field_w = 0
		self.cl_field_h = 0

		self.create()

	def create(self):
		self.cl_group = clutter.Group()

		self.cl_bg = clutter.Rectangle()
		self.cl_bg.set_border_width(2)
		self.cl_bg.set_border_color(black)
		self.cl_bg.set_color(white)
		self.cl_bg.set_size(self.width, self.height)
		self.cl_group.add(self.cl_bg)
		
		self.cl_title = clutter.Text()
		self.cl_title.set_text(self.title)
		self.cl_title.set_position(0, 0)
		self.cl_group.add(self.cl_title)

		self.cl_field_w = self.width - 2*self.MARGIN_LEFT
		self.cl_field_h = self.height - 2*self.MARGIN_BOT

		self.cl_xaxis_bg = clutter.CairoTexture(self.cl_field_w, self.MARGIN_BOT)
		self.cl_xaxis_bg.set_position(self.MARGIN_LEFT, self.height-self.MARGIN_BOT)
		self.cl_group.add(self.cl_xaxis_bg)

		self.cl_yaxis_bg = clutter.CairoTexture(self.MARGIN_LEFT, self.cl_field_h)
		self.cl_yaxis_bg.set_position(0, self.MARGIN_BOT)
		self.cl_group.add(self.cl_yaxis_bg)

		self.cl_field = clutter.Rectangle()
		self.cl_field.set_border_width(1)
		self.cl_field.set_border_color(black)
		self.cl_field.set_color(white)
		self.cl_field.set_size(self.cl_field_w, self.cl_field_h)
		self.cl_field.set_position(self.MARGIN_LEFT, self.MARGIN_BOT)
		self.cl_group.add(self.cl_field)

		self.cl_curve = clutter.CairoTexture(self.cl_field_w, self.cl_field_h)
		self.cl_curve.set_position(self.MARGIN_LEFT, self.MARGIN_BOT)
		self.cl_group.add(self.cl_curve)

		self.stage.add(self.cl_group)

	def draw_axes(self):

	def draw_curve(self, points):
		def cvt(p):
			np = [(p[0] - self.x_min)*float(self.cl_field_w)/(self.x_max - self.x_min),
		          self.cl_field_h - (p[1] - self.y_min)*float(self.cl_field_h)/(self.y_max -
																		  self.y_min)]
			return np

		self.cl_curve.clear()
		ctxt = self.cl_curve.cairo_create()
		ctxt.scale(1.0, 1.0)
		ctxt.set_source_color(black)

		p = cvt(points[0])
		ctxt.move_to(p[0], p[1])

		for p in points[1:]:
			pc = cvt(p)
			#print pc
			ctxt.line_to(pc[0], pc[1])
		#ctxt.close_path()
		ctxt.stroke()
		del ctxt


import math
import glib

pts = [[x/100.0, math.sin(x/100.0)] for x in range(0, 628) ]

if __name__ == "__main__":
	
	glib.threads_init()
	clutter.threads_init()
	clutter.init()

	stg = clutter.Stage()
	stg.set_size(320, 240)
	sco = ScopeActor(stg, 320, 240, "Scope test")
	stg.show()
	
	def movecurve():
		global pts
		fx = pts[-0][0]
		for p in pts[1:]:
			nx = p[0]]
			p[0] = fx
			fx = nx
			
		pts[0][0] = fx
		pts.sort()
		sco.draw_curve(pts)
		return True

	glib.idle_add(movecurve)
	sco.draw_curve(pts)
	clutter.main()	

