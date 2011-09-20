
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
	char shm_id[64];
	int shm_fd;
	int shm_size;
	void * shm_ptr;
	int chan_count;
	int chan_size;
	int chan_pos;
	int trig_triggered;
	int trig_channel;
	int trig_op;
	int trig_mode;
	mfp_sample trig_thresh;
} buf_info;

#define TRIG_BANG 0
#define TRIG_THRESH 1
#define TRIG_EXT 2

#define TRIG_GT 0
#define TRIG_LT 1

static void 
init(mfp_processor * proc) 
{
	buf_info * d = g_malloc(sizeof(buf_info));
	int pid = getpid();
	struct timeval tv;

	gettimeofday(&tv, NULL);
	sprintf(d->shm_id, "/mfp_buffer_%05d_%06d_%06d", pid, tv.tv_sec, tv.tv_usec); 
	d->shm_fd = shm_open(d->shm_name, O_RDWR|O_CREAT, S_IRWXU); 
	d->shm_ptr = NULL;
	proc->data = d;
	return;
}

static int 
process(mfp_processor * proc) 
{
	int dstart = 0;
	int channel, tocopy;
	buf_info d = (buf_info *)(proc->data);
	mfp_block * trig_block;

	if(d->trig_triggered == 0) {
		if(d->trig_mode == TRIG_EXT) {
			trig_block = proc->inlet_buf[proc->inlet_conn->length - 1];
		}
		if(d->trig_mode == TRIG_THRESH) {
			if(d->trig_channel > proc->inlet_conn->length-1) {
				return -1;
			}
			trig_block = proc->inlet_buf[d->trig_channel]
		}
		if(d->trig_mode != TRIG_BANG) {
			while(d->trig_triggered == 0) {
				if((d->trig_op == TRIG_GT) && (trig_block->data[dstart] > d->trig_thresh)) {
					d->trig_triggered = 1;
				}
				else if ((d->trig_op == TRIG_LT)  && (trig_block->data[dstart] < d->trig_thresh)) {
					d->trig_triggered = 1;
				}

				if(d->trig_triggered == 0)
					dstart++;
				if (dstart >= trig_block->blocksize)
					break;
			}
		}
	}

	if(d->trig_triggered) {
		/* copy rest of the block or available space */
		tocopy = min(mfp_blocksize-dstart, d->chan_size-d->chan_pos);

		/* iterate over channels */
		for(channel=0; channel < d->chan_count; channel++) {
			memcpy((float *)d->shm_ptr + (channel*d->chan_size) + d->chan_pos,
					proc->inlet_buf[channel]->data + dstart,
					sizeof(mfp_sample)*tocopy);
		}

		/* if we reached the end of the buffer, untrigger */
		d->chan_pos += tocopy;
		if(d->chan_pos >= d->chan_size) {
			d->trig_triggered = 0;
			d->chan_pos = 0;
		}

	}

	return 0;
}

static void
destroy(mfp_processor * proc) 
{
	buf_info * d = (buf_info *)(proc->data);
	if(d->shm_ptr != NULL) 
		munmap(d->shm_ptr);

	if(d->shm_fd > -1) {
		close(d->shm_fd);
		shm_unlink(d->shm_id);
	}
	
	g_free(d);
	proc->data = NULL;

	return;

}

static void
buffer_resize(buf_info * d, int size)
{
	if(d->shm_ptr != NULL) {
		munmap(d->shm_ptr);
		d->shm_ptr = NULL;
	}
	ftruncate(d->shm_fd, size);
	d->shm_ptr = mmap(NULL,  size, PROT_READ|PROT_WRITE, MAP_SHARED, d->shm_fd, 0);
}


static void
config(mfp_processor * proc) 
{
	gpointer size_ptr g_hash_table_lookup(proc->params, "size");
	gpointer channels_ptr g_hash_table_lookup(proc->params, "channels");
	gpointer trigmode_ptr g_hash_table_lookup(proc->params, "trig_mode");
	gpointer trigchan_ptr g_hash_table_lookup(proc->params, "trig_chan");
	gpointer trigthresh_ptr g_hash_table_lookup(proc->params, "trig_thresh");
	gpointer trigbang_ptr g_hash_table_lookup(proc->params, "trig_bang");

	buf_info * d = (buf_info *)(proc->data);

	if ((size_ptr != NULL) || (channels_ptr != NULL)) {
		if(size_ptr != NULL) {
			d->chan_size = *(int *)size_ptr;
		}
		if(channels_ptr != NULL) {
			d->chan_count = *(int *)channels_ptr;
		}
	
		buffer_resize(d, d->chan_count*d->chan_size*sizeof(mfp_sample))
	}

	if (trigmode_ptr != NULL) {
		d->trig_mode = *(int *)trigmode_ptr;
	}

	if (trigchan_ptr != NULL) {
		d->trig_channel = *(int *)trigchan_ptr;
	}

	if (trigthresh_ptr != NULL) {
		d->trig_thresh = *(float *)trigthresh_ptr;
	}
	return;
}

mfp_procinfo *  
init_builtin_noise(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	
	p->name = strdup("buffer");
	p->is_generator = 0;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	return p;
}


