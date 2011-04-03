
#include "cubic.h"


typedef struct {
	float x_min;
	float x_max;
	float c0;
	float c1;
	float c2;
	float c3;
} cubic_segment;

typedef struct {
	cubic_segment * segments;
	int num_segments;
	int last_segment;
} cubic_estimator;


cubic_estimator * 
cubic_new(int segments) 
{
	cubic_data * d = (cubic_data *)g_malloc(sizeof(cubic_data));
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


