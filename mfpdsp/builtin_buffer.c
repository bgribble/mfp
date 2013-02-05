
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <sys/time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <unistd.h>
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
    int trig_enabled;
    int trig_chanmask;
    int trig_pretrigger;
    int trig_triggered;
    int trig_channel;
    int trig_op;
    int trig_mode;
    int trig_repeat;
    int clip_chanmask;
    int clip_state;
    int clip_repeat;
    int clip_start;
    int clip_end; 
    int clip_pos;

    mfp_sample trig_thresh;
} buf_info;

/* trig_mode values */ 
#define TRIG_BANG 0
#define TRIG_THRESH 1
#define TRIG_EXT 2

/* trig_repeat and clip_repeat values */ 
#define REPEAT_ONESHOT 0 
#define REPEAT_CONTIN  1

/* trig_op values */ 
#define TRIG_GT 0 
#define TRIG_LT 1

/* response types */ 
#define RESP_TRIGGERED 0
#define RESP_BUFID 1
#define RESP_BUFSIZE 2
#define RESP_BUFCHAN 3
#define RESP_RATE 4 
#define RESP_OFFSET 5
#define RESP_BUFRDY 6

/* clip_state values */ 
#define CLIP_IDLE 0 
#define CLIP_PLAYING 1
#define CLIP_RECORDING 2

static void 
init(mfp_processor * proc) 
{
    buf_info * d = g_malloc0(sizeof(buf_info));

    d->shm_id[0] =0;
    d->shm_fd = -1;
    d->shm_size = 0;
    d->shm_ptr = NULL;
    d->chan_count=0;
    d->chan_size = 0;
    d->chan_pos = 0;
    d->trig_channel = 0;
    d->trig_mode = 0;
    d->trig_op = 0;
    d->trig_thresh = 0;
    d->trig_triggered = 0;
    d->trig_pretrigger = 0;
    d->trig_enabled = 1;
    d->trig_repeat = 1;
    d->trig_chanmask = 0;
    d->clip_chanmask = 0;
    d->clip_repeat = 0;
    d->clip_start = -1;
    d->clip_end = -1;
    d->clip_pos = 0;
    proc->data = d;

    return;
}

static int 
process(mfp_processor * proc) 
{
    int dstart = 0;
    int channel, tocopy;
    buf_info * d = (buf_info *)(proc->data);
    mfp_block * trig_block;
    mfp_sample * outptr, *inptr;
    int inpos, outpos;

    /* if not currently capturing, check for trigger conditions */ 
    if(d->trig_triggered == 0 && d->trig_enabled) {
        if(d->trig_mode == TRIG_EXT) {
            trig_block = proc->inlet_buf[proc->inlet_conn->len - 1];
        }
        if(d->trig_mode == TRIG_THRESH) {
            if(d->trig_channel > proc->inlet_conn->len-1) {
                return -1;
            }
            trig_block = proc->inlet_buf[d->trig_channel];
        }
        if(!(d->trig_mode == TRIG_BANG)) {
            while(d->trig_triggered == 0) {
                if (d->trig_pretrigger == 0) { 
                    if((d->trig_op == TRIG_GT) 
                        && (trig_block->data[dstart] <= d->trig_thresh)) {
                        d->trig_pretrigger = 1;
                    }
                    else if((d->trig_op == TRIG_LT) 
                        && (trig_block->data[dstart] >= d->trig_thresh)) {
                        d->trig_pretrigger = 1;
                    }
                }
                else { 
                    if((d->trig_op == TRIG_GT) 
                        && (trig_block->data[dstart] > d->trig_thresh)) {
                        d->trig_triggered = 1;
                        d->trig_pretrigger = 0;
                    }
                    else if ((d->trig_op == TRIG_LT)  
                        && (trig_block->data[dstart] < d->trig_thresh)) {
                        d->trig_triggered = 1;
                        d->trig_pretrigger = 0;
                    }
                }
                if(d->trig_triggered == 0)
                    dstart++;
                if (dstart >= trig_block->blocksize)
                    break;
            }
            if (d->trig_triggered) {
                d->clip_pos = 0;
                d->clip_start = 0;
                d->clip_state = CLIP_PLAYING;
                mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 1);
            }
        }
    }

    /* if we are triggered, copy data from inlets to buffer */
    if(d->trig_triggered) {
        /* copy rest of the block or available space */
        tocopy = MIN(mfp_blocksize-dstart, d->chan_size-d->chan_pos);

        /* iterate over channels */
        for(channel=0; channel < d->chan_count; channel++) {
            if(!((1 << channel) & d->trig_chanmask)) {
                memcpy((float *)d->shm_ptr + (channel*d->chan_size) + d->chan_pos,
                        proc->inlet_buf[channel]->data + dstart,
                        sizeof(mfp_sample)*tocopy);
            }
        }

        /* if we reached the end of the buffer, untrigger */
        d->chan_pos += tocopy;
        if(d->chan_pos >= d->chan_size) {
            d->trig_triggered = 0;
            d->chan_pos = 0;
            if (d->trig_repeat == REPEAT_ONESHOT) {
                d->trig_enabled = 0;
            }
            mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 0);
        }

    }

    /* zero output buffer in any case */ 
    mfp_block_zero(proc->outlet_buf[0]);

    /* if we are playing, copy data from the buffer to the outlet */ 
    if (d->clip_state != CLIP_IDLE) {
        /* accumulate non-masked channels in the output buffer */ 
        for(channel=0; channel < d->chan_count; channel++) {
            if(!((1 << channel) & d->clip_chanmask)) {
                outptr = proc->outlet_buf[0]->data;
                inptr = (float *)(d->shm_ptr) + (channel*d->chan_size);
                inpos = d->clip_pos;
                for(outpos = 0; outpos < mfp_blocksize; outpos++) {
                    if (inpos < d->clip_end) {
                        *outptr++ += inptr[inpos++];
                    }
                    else if (d->clip_repeat == REPEAT_ONESHOT) {
                        *outptr++ = 0;
                    }
                    else {
                        inpos = d->clip_start;
                        *outptr ++ += inptr[inpos++];
                    }
                }
            } 
        }
        
        /* update d->clip_pos for next block */ 
        if (d->clip_pos + mfp_blocksize < d->clip_end) {
            d->clip_pos += mfp_blocksize;
        }
        else if (d->clip_repeat == REPEAT_ONESHOT) {
            d->clip_pos = d->clip_start;
            d->clip_state = CLIP_IDLE;
        }
        else {
            d->clip_pos = 
                d->clip_start + ((d->clip_pos - d->clip_start + mfp_blocksize) 
                                 % (d->clip_end - d->clip_start));
        }

    }

    return 0;
}

static void
destroy(mfp_processor * proc) 
{
    buf_info * d = (buf_info *)(proc->data);
    if(d->shm_ptr != NULL) 
        munmap(d->shm_ptr, d->shm_size);

    if(d->shm_fd > -1) {
        close(d->shm_fd);
        shm_unlink(d->shm_id);
    }
    
    g_free(d);
    proc->data = NULL;

    return;

}

static void
buffer_alloc(buf_info * d)
{
    int size = d->chan_count*d->chan_size*sizeof(mfp_sample);
    int pid = getpid();
    struct timeval tv;

    gettimeofday(&tv, NULL);

    snprintf(d->shm_id, 64, "/mfp_buffer_%05d_%06d_%06d", pid, (int)tv.tv_sec, (int)tv.tv_usec); 
    d->shm_fd = shm_open(d->shm_id, O_RDWR|O_CREAT, S_IRWXU); 
    
    if(d->shm_ptr != NULL) {
        munmap(d->shm_ptr, d->shm_size);
        d->shm_ptr = NULL;
    }
    ftruncate(d->shm_fd, size);
    d->shm_size = size;
    d->shm_ptr = mmap(NULL,  size, PROT_READ|PROT_WRITE, MAP_SHARED, d->shm_fd, 0);
    if (d->shm_ptr == NULL) {
        printf("mmap() failed... %d (%s)\n", d->shm_fd, sys_errlist[errno]);
    }
    if ((d->clip_start < 0) || (d->clip_start > d->chan_size)) {
        d->clip_start = 0;
    }
    if ((d->clip_end < 0) || (d->clip_end > d->chan_size)) {
        d->clip_end = d->chan_size;
    }

}


static void
config(mfp_processor * proc) 
{
    gpointer size_ptr = g_hash_table_lookup(proc->params, "size");
    gpointer channels_ptr = g_hash_table_lookup(proc->params, "channels");
    gpointer trigmode_ptr = g_hash_table_lookup(proc->params, "trig_mode");
    gpointer trigchan_ptr = g_hash_table_lookup(proc->params, "trig_chan");
    gpointer trigthresh_ptr = g_hash_table_lookup(proc->params, "trig_thresh");
    gpointer trigtrig_ptr = g_hash_table_lookup(proc->params, "trig_triggered");
    gpointer trigrept_ptr = g_hash_table_lookup(proc->params, "trig_repeat");
    gpointer trigenable_ptr = g_hash_table_lookup(proc->params, "trig_enabled");
    gpointer trigmask_ptr = g_hash_table_lookup(proc->params, "trig_chanmask");

    gpointer clipplay_ptr = g_hash_table_lookup(proc->params, "clip_play");
    gpointer cliprec_ptr = g_hash_table_lookup(proc->params, "clip_rec");
    gpointer cliprepeat_ptr = g_hash_table_lookup(proc->params, "clip_repeat");
    gpointer clipstart_ptr = g_hash_table_lookup(proc->params, "clip_start");
    gpointer clipend_ptr = g_hash_table_lookup(proc->params, "clip_end");
    gpointer clipmask_ptr = g_hash_table_lookup(proc->params, "clip_chanmask");

    buf_info * d = (buf_info *)(proc->data);
    int new_size=d->chan_size, new_channels=d->chan_count;

    if ((size_ptr != NULL) || (channels_ptr != NULL)) {
        if(size_ptr != NULL) {
            new_size = (int)(*(float *)size_ptr);
        }
        if(channels_ptr != NULL) {
            new_channels = (int)(*(float *)channels_ptr);
        }

        if ((new_size != d->chan_size) || (new_channels != d->chan_count)) {
            d->chan_size = new_size;
            d->chan_count = new_channels;
            d->chan_pos = 0;
            buffer_alloc(d);

            mfp_dsp_send_response_str(proc, RESP_BUFID, d->shm_id);
            mfp_dsp_send_response_int(proc, RESP_BUFSIZE, d->chan_size);
            mfp_dsp_send_response_int(proc, RESP_BUFCHAN, d->chan_count);
            mfp_dsp_send_response_int(proc, RESP_RATE, mfp_samplerate);
            mfp_dsp_send_response_bool(proc, RESP_BUFRDY, 1);
        }
    }

    if (trigmode_ptr != NULL) {
        d->trig_mode = *(float *)trigmode_ptr;
    }

    if (trigchan_ptr != NULL) {
        d->trig_channel = *(float *)trigchan_ptr;
    }

    if (trigthresh_ptr != NULL) {
        d->trig_thresh = *(float *)trigthresh_ptr;
    }

    if (trigrept_ptr != NULL) {
        d->trig_repeat = (int)(*(float *)trigrept_ptr);
    }

    if (trigtrig_ptr != NULL) {
        if ((*(float *)trigtrig_ptr) > 0.5) {
            d->trig_triggered = 1;
        }
        else {
            d->trig_triggered = 0;
        }
        g_hash_table_remove(proc->params, "trig_triggered");
        mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, d->trig_triggered);
    }

    if (trigenable_ptr != NULL) {
        d->trig_enabled = (int)(*(float *)trigenable_ptr);
    }

    if (trigmask_ptr != NULL) {
        d->trig_chanmask = (int)(*(float *)trigmask_ptr);
    }

    if (cliprepeat_ptr != NULL) {
        d->clip_repeat = (int)(*(float *)cliprepeat_ptr);
    }

    if (clipstart_ptr != NULL) {
        d->clip_start = (int)(*(float *)clipstart_ptr);
    }

    if (clipend_ptr != NULL) {
        d->clip_end = (int)(*(float *)clipend_ptr);
    }

    if (clipplay_ptr != NULL) {
        d->clip_state = CLIP_PLAYING;
        d->clip_pos = d->clip_start;
        g_hash_table_remove(proc->params, "clip_play");
    }
    
    if (clipmask_ptr != NULL) {
        d->clip_chanmask = (int)(*(float *)clipmask_ptr);
    }

    return;
}

mfp_procinfo *  
init_builtin_buffer(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    
    p->name = strdup("buffer~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "buf_id", (gpointer)PARAMTYPE_STRING);
    g_hash_table_insert(p->params, "channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "size", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_thresh", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_mode", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_chan", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_op", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_triggered", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_repeat", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_enabled", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_chanmask", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clip_repeat", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clip_play", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clip_rec", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clip_start", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clip_end", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clip_chanmask", (gpointer)PARAMTYPE_FLT);

    return p;
}


