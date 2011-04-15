
#include "cubic.h"

typedef struct {
	float c0;
	float c1;
	float c2;
	float c3;
} cspline_segment;

typedef struct {
	cspline_segment * segments;
	int num_segments;
	float domain_start;
	float domain_end;
} cspline;


cspline * 
cspline_new(int segments) 
{
	cspline * c = g_malloc(sizeof(cspline));
	cspline_segment * d = (cspline_segment *)g_malloc(segments*sizeof(cspline_segment));

	c->num_segments = segments;
	c->segments = d;
}

void
cspline_init(cspline * self, float domain_start, float domain_end, float *segments)
{
	int seg;
	float * cur_pos;
	for(seg=0; seg < self->num_segments; seg++) {
		cur_pos = segments + 4*seg;
		self->segments[seg].c0 = *cur_pos++;
		self->segments[seg].c1 = *cur_pos++;
		self->segments[seg].c2 = *cur_pos++;
		self->segments[seg].c3 = *cur_pos++;
	}
	self->domain_start = domain_start;
	self->domain_end = domain_end;
}

int
cspline_block_eval(cspline * self, mfp_sample * in, mfp_sample * out)
{

}



float 
cubic_eval(cubic_estimator * self, float x)
{
	int scount;
	int segs = self->num_segments;
	int last = self->last_segment; 
	cubic_segment * s;
	float rval; 

	for(scount=0; scount < segs; scount++) {
		s = self->segments[(scount + last) % segs];
		if ((x >= s->x_min) && (x < s->x_max)) {
			rval = s->c0 + x*s->c1 + x*x*s->c2 + x*x*x*s->c3;
			self->last_segment = (scount+last) % segs;
			break;
		}
		else if ((x > s->x_max) && (((scount+last) % segs) == segs-1)) {
			rval = s->c0 + x*s->c1 + x*x*s->c2 + x*x*x*s->c3;
			break;	
		}
		else if ((x < s->x_min) && (((scount+last) % segs) == 0)) {
			rval = s->c0 + x*s->c1 + x*x*s->c2 + x*x*x*s->c3;
			break;	
		}
	}
	return rval;
}


