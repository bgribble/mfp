#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
	int start_frame;
	float end_val;
	int end_frame;
} segment;

typedef struct {
	int cur_frame;
	int cur_segment;
	float start_val;
	float cur_val;
	segment * segv;
	int nsegs;
} builtin_line_data;

static void
config(mfp_processor * proc) 
{
	builtin_line_data * pdata = (builtin_line_data *)proc->data;
	GArray * segments_raw = (GArray *)g_hash_table_lookup(proc->params, "segments");
	gpointer position_ptr = g_hash_table_lookup(proc->params, "position");
	float delay_ms, end_val, ramp_ms, frames_per_ms;
	segment * segments = NULL;
	int numsegs = 0;
	int rawpos = 0;
	int scount;
	int framebase = 0;
	
	frames_per_ms = mfp_samplerate / 1000.0; 
	printf("line config enter\n");

	/* populate new segment data if passed */
	if (segments_raw != NULL) {
		if(segments_raw->len == 0) {
			numsegs = 0;
		}
		else {
			numsegs = (segments_raw->len)/3; 
			printf("%d segments\n", numsegs);
			segments = g_malloc(numsegs * sizeof(segment));
		}

		rawpos = 0;
		framebase = 0;
		for (scount=0; scount < numsegs; scount++) {
			delay_ms = g_array_index(segments_raw, float, rawpos++);
			end_val = g_array_index(segments_raw, float, rawpos++);
			ramp_ms = g_array_index(segments_raw, float, rawpos++);
			printf("  segment %d: %f %f %f\n", scount, delay_ms, end_val, ramp_ms);
			segments[scount].start_frame = framebase + (int)(delay_ms*frames_per_ms + 0.5);
			segments[scount].end_val = end_val;

			/* every segment is at least 1 frame */
			if (ramp_ms * frames_per_ms < 0.5) {
				framebase++;
			}
			segments[scount].end_frame = framebase + (int)((delay_ms+ramp_ms)*frames_per_ms + 0.5);
			framebase = segments[scount].end_frame;
		}
		if (pdata->segv != NULL) 
			g_free(pdata->segv);

		pdata->segv = segments;
		pdata->nsegs = numsegs;
		pdata->cur_frame = 0;
		pdata->cur_segment = 0;
		pdata->start_val = pdata->cur_val;
		g_hash_table_replace(proc->params, g_strdup("segments"), NULL);
	}

	/* position */
	if(position_ptr != NULL) {
		pdata->cur_frame = (int)(*(float *)position_ptr * frames_per_ms + 0.5);
		for(scount=0; scount < pdata->nsegs; scount++) {
			if(pdata->cur_frame >= pdata->segv[scount].start_frame &&
			   pdata->cur_frame < pdata->segv[scount].end_frame) {
				pdata->cur_segment = scount;
			}
		}

	}
}

static int 
process(mfp_processor * proc) 
{
	builtin_line_data * data = ((builtin_line_data *)(proc->data));
	segment * cseg = data->segv + data->cur_segment;
	int cframe = data->cur_frame;
	double slope, offset;
	int scount;
	float * sample = proc->outlet_buf[0]->data;

	printf("line.process()\n");

	if (sample == NULL) {
		return 0;
	}
	
	if (data == NULL) {
		return 0;
	}

	if (data->nsegs == 0) {
		return 0;
	}

	slope = ((double)(cseg->end_val - data->start_val))/(cseg->end_frame-cseg->start_frame);
	offset = data->start_val;

	printf("line.process really starting\n");

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		if (cframe < cseg->start_frame) {
			*sample++ = data->cur_val;
		}
		else if (cframe > cseg->end_frame) {
			*sample++ = data->cur_val;
		}
		else if (cframe == cseg->end_frame) {
			data->cur_val = cseg->end_val;
			*sample++ = data->cur_val;
			if ((data->cur_segment+1) < data->nsegs) {
				data->cur_segment++;
				data->start_val = data->cur_val;
				cseg ++;
			}
		}
		else if (cframe == cseg->start_frame) {
			slope = ((double)(cseg->end_val - data->start_val))/(cseg->end_frame-cseg->start_frame);
			offset = data->cur_val;
			*sample++ = data->cur_val;
		}
		else {
			data->cur_val = (float)((double)(cframe - cseg->start_frame)*slope + offset); 
			*sample++ = data->cur_val; 
		}
		cframe++;
		data->cur_frame = cframe;
	}
	
	return 0;
}

static void 
init(mfp_processor * proc) 
{
	builtin_line_data * p = g_malloc(sizeof(builtin_line_data));

	proc->data = p; 
	
	p->segv = NULL;
	p->nsegs = 0;
	p->cur_frame = 0;
	p->cur_segment = 0;
	p->start_val = 0.0;
	p->cur_val = 0.0;
}

static void
destroy(mfp_processor * proc) 
{
	builtin_line_data * p;
	if (proc->data != NULL) {
		p = (builtin_line_data *)(proc->data);
		if (p->segv != NULL) {
			g_free(p->segv);
			p->segv = NULL;
		}
		g_free(proc->data);
		proc->data = NULL;
	}
}


mfp_procinfo *  
init_builtin_line(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("line");
	p->is_generator = GENERATOR_ALWAYS;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "segments", (gpointer)PARAMTYPE_FLTARRAY);
	g_hash_table_insert(p->params, "position", (gpointer)PARAMTYPE_FLT);

	return p;
}


