
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
    int  shm_fd;
    int  buf_type;
    void * buf_ptr;
    int  buf_chancount;
    int  buf_chansize;
    int  buf_size;
    int  buf_ready; 
} buf_info;


typedef struct {
    buf_info buf_active;
    buf_info buf_to_alloc; 

    mfp_sample * buf_base;  
    int chan_count;
    int chan_size;
    
    /* trigger settings (for TRIG_THRESH, TRIG_EXT modes */ 
    int trig_pretrigger;
    int trig_channel;
    int trig_op;
    mfp_sample trig_thresh;

    /* record settings */ 
    int play_channels;
    int rec_channels;
    int rec_enabled;

    /* region definition (for LOOP modes, set by REC_LOOPSET) */ 
    int region_start;
    int region_end; 

    int buf_pos;
    int buf_mode;
    int buf_state;

} builtin_buffer_data;

/* buf_type values */ 
#define BUFTYPE_PRIVATE 0
#define BUFTYPE_SHARED 1 

/* buf_mode values */ 
#define REC_BANG 0        /* on Bang, record buffer and stop */ 
#define REC_LOOPSET 1     /* record, establishing region_start and region_end */ 
#define REC_LOOP 2        /* continuously record between region_start and region_end */ 
#define REC_TRIG_THRESH 3 /* When trig_channel crosses trig_thresh, rec buffer and stop */ 
#define REC_TRIG_EXT 4    /* when external input crosses trig_thresh, rec buffer and stop */ 
#define PLAY_BANG 5       /* play buffer once */ 
#define PLAY_LOOP 6       /* loop over region */ 

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
#define RESP_LOOPSTART 7

/* buf_state values */ 
#define BUF_IDLE 0 
#define BUF_ACTIVE 1

static void 
init(mfp_processor * proc) 
{
    builtin_buffer_data * d = g_malloc0(sizeof(builtin_buffer_data));

    d->buf_active.shm_id[0] = 0;
    d->buf_active.shm_fd = -1;
    d->buf_active.buf_type = BUFTYPE_SHARED;
    d->buf_active.buf_size = 0;
    d->buf_active.buf_ptr = NULL;
    d->buf_active.buf_ready = 0; 

    d->buf_to_alloc.shm_id[0] = 0;
    d->buf_to_alloc.shm_fd = -1;
    d->buf_to_alloc.buf_type = BUFTYPE_SHARED;
    d->buf_to_alloc.buf_size = 0;
    d->buf_to_alloc.buf_ptr = NULL;
    d->buf_to_alloc.buf_ready = 0; 

    d->buf_base = NULL;
    d->chan_count = 0;
    d->chan_size = 0;
    d->trig_channel = 0;
    d->trig_pretrigger = 0;
    d->trig_op = TRIG_GT;
    d->trig_thresh = 0.0;
    
    d->rec_enabled = 0;
    d->rec_channels = 0;
    d->play_channels = 0;

    d->buf_pos = 0;
    d->buf_mode = REC_BANG; 
    d->buf_state = BUF_IDLE;

    d->region_start = 0;
    d->region_end = 0;
    
    proc->data = d;

    return;
}

static int 
process(mfp_processor * proc) 
{
    builtin_buffer_data * d = (builtin_buffer_data *)(proc->data);
    int dstart = 0;
    int channel, tocopy;
    mfp_block * trig_block;
    mfp_sample * outptr, *inptr;
    int inpos, outpos;
    int loopstart=0; 

    if (d->buf_base == NULL) {
        return 0;
    }

    /* if not currently capturing, check for trigger conditions */ 
    if(d->buf_state == BUF_IDLE && d->rec_enabled) {
        if ((d->buf_mode == REC_TRIG_EXT) || (d->buf_mode == REC_TRIG_THRESH)) {
            /* trig_block is the data we will be looking at to find a trigger condition */
            switch (d->buf_mode) {
                case REC_TRIG_EXT: 
                    trig_block = proc->inlet_buf[proc->inlet_conn->len - 1];
                    break;

                case REC_TRIG_THRESH:
                    if(d->trig_channel > proc->inlet_conn->len-1) 
                        return -1;
                    trig_block = proc->inlet_buf[d->trig_channel];
                    break;
            }

            /* iterate over trig_block looking for a trigger */ 
            dstart = 0;
            while(d->buf_state == BUF_IDLE) {
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
                        d->buf_state = BUF_ACTIVE;
                        d->trig_pretrigger = 0;
                    }
                    else if ((d->trig_op == TRIG_LT)  
                        && (trig_block->data[dstart] < d->trig_thresh)) {
                        d->buf_state = BUF_ACTIVE;
                        d->trig_pretrigger = 0;
                    }
                }
                if(d->buf_state == BUF_IDLE) {
                    dstart++;
                }

                if (dstart >= trig_block->blocksize)
                    break;
            }

            if (d->buf_state == BUF_ACTIVE) {
                d->region_start = 0;
                d->region_end = d->chan_size;
                d->buf_pos = 0;

                mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 1);
            }
        }
        else if ((d->buf_mode == REC_LOOPSET) || (d->buf_mode == REC_LOOP)) {
            if (d->buf_mode == REC_LOOPSET) {
                d->region_start = 0;
                d->region_end = 0;
                d->buf_pos = 0;
            }

            d->buf_state = BUF_ACTIVE;
            loopstart = 1;
        }
    }

    /* zero output buffer in preparation for PLAY operations */ 
    mfp_block_zero(proc->outlet_buf[0]);

    /* if we are playing, copy data from the buffer to the outlet */ 
    if (d->buf_state != BUF_IDLE) {
        /* accumulate non-masked channels in the output buffer */ 
        for(channel=0; channel < d->chan_count; channel++) {
            if((1 << channel) & d->play_channels) {
                outptr = proc->outlet_buf[0]->data;
                inptr = (float *)(d->buf_base) + (channel*d->chan_size);
                inpos = d->buf_pos;
                for(outpos = 0; outpos < mfp_blocksize; outpos++) {
                    if (inpos < d->region_end) {
                        outptr[outpos] += inptr[inpos++];
                    }
                    else if ((d->buf_mode == PLAY_LOOP) || (d->buf_mode == REC_LOOP)) {
                        inpos = d->region_start;
                        outptr[outpos] += inptr[inpos++];
                    }
                    else {
                        outptr[outpos] = 0;
                    }
                }
            } 
        }
    }

    /* if we are triggered, copy data from inlets to buffer */
    if(d->buf_state == BUF_ACTIVE && d->rec_enabled) {
        tocopy = MIN(mfp_blocksize-dstart, d->chan_size - d->buf_pos);

        /* iterate over channels, grabbing data if channel is active */
        for(channel=0; channel < d->chan_count; channel++) {
            if((1 << channel) & d->rec_channels) {
                if (d->buf_mode == REC_LOOP) {
                    /* accumulate into buffer */ 
                    outptr = (float *)d->buf_base + (channel*d->chan_size);
                    outpos = d->buf_pos;
                    inptr = proc->inlet_buf[channel]->data;
                    for (inpos = 0; inpos < tocopy; inpos++) {
                        outptr[outpos++] = inptr[inpos];
                        if (outpos > d->region_end) {
                            outpos = d->region_start;
                        }
                    }
                }
                else {
                    memcpy((float *)d->buf_base + (channel*d->chan_size) + d->buf_pos,
                            proc->inlet_buf[channel]->data + dstart,
                            sizeof(mfp_sample)*tocopy);
                }
            }
        }

    }

    if (d->buf_state != BUF_IDLE) {
        /* update d->buf_pos for next block */ 
        if (d->buf_mode == REC_LOOPSET) {
            d->buf_pos = MIN(d->buf_pos + mfp_blocksize, d->chan_size);
            d->region_end = d->buf_pos;
        }
        else if (d->buf_pos + mfp_blocksize < d->region_end) {
            d->buf_pos += mfp_blocksize;
        }
        else if ((d->buf_mode == PLAY_LOOP) || (d->buf_mode == REC_LOOP)) {
            d->buf_pos = 
                d->region_start + ((d->buf_pos - d->region_start + mfp_blocksize) 
                        % (d->region_end - d->region_start));
            loopstart = 1;
        }
        else {
            d->buf_pos = d->region_start;
            if (d->buf_state == REC_LOOPSET) {
                d->region_end = d->buf_pos;
            }
            d->buf_state = BUF_IDLE;
        }
        /* if we reached the end of the buffer, untrigger */
        switch (d->buf_mode) {
            case REC_BANG:
                if(loopstart == 1) {
                    d->buf_state = BUF_IDLE;
                    d->rec_enabled = 0;
                }
                break;

            case REC_TRIG_THRESH:
            case REC_TRIG_EXT:
                if(loopstart == 1) {
                    d->buf_state = BUF_IDLE;
                    d->rec_enabled = 0;
                    d->trig_pretrigger = 0;
                }
                break;

            case REC_LOOPSET:
                if (d->buf_pos > d->region_end) 
                    d->region_end = d->buf_pos;

                break;
        }
    }

    if (d->buf_state == BUF_IDLE) {
        mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 0);
    }
    if(loopstart > 0) {
        mfp_dsp_send_response_bool(proc, RESP_LOOPSTART, 1);
    }


    return 0;
}

static void
destroy(mfp_processor * proc) 
{
    builtin_buffer_data * d = (builtin_buffer_data *)(proc->data);
    if(d->buf_active.buf_ptr != NULL) {
        if (d->buf_active.buf_type == BUFTYPE_SHARED) 
            munmap(d->buf_active.buf_ptr, d->buf_active.buf_size);
        else {
            g_free(d->buf_active.buf_ptr);
        }

        if(d->buf_active.shm_fd > -1) {
            close(d->buf_active.shm_fd);
            shm_unlink(d->buf_active.shm_id);
        }
    }

    g_free(d);
    proc->data = NULL;

    return;

}

static void
shared_buffer_alloc(buf_info * buf)
{
    int size = buf->buf_chancount * buf->buf_chansize * sizeof(mfp_sample);
    int pid = getpid();
    struct timeval tv;

    gettimeofday(&tv, NULL);

    snprintf(buf->shm_id, 64, "/mfp_buffer_%05d_%06d_%06d", 
             pid, (int)tv.tv_sec, (int)tv.tv_usec); 
    buf->shm_fd = shm_open(buf->shm_id, O_RDWR|O_CREAT, S_IRWXU); 
    
    if(buf->buf_ptr != NULL) {
        munmap(buf->buf_ptr, buf->buf_size);
        buf->buf_ptr = NULL;
    }
    ftruncate(buf->shm_fd, size);
    buf->buf_size = size;
    buf->buf_ptr = mmap(NULL,  size, PROT_READ|PROT_WRITE, MAP_SHARED, buf->shm_fd, 0);
    if (buf->buf_ptr == NULL) {
        printf("mmap() failed... %d (%s)\n", buf->shm_fd, sys_errlist[errno]);
    }
}

static void
buffer_activate(builtin_buffer_data * d) 
{
    d->buf_to_alloc.buf_ready = ALLOC_IDLE;
    memcpy(&(d->buf_active), &(d->buf_to_alloc), sizeof(buf_info));
    d->chan_count = d->buf_active.buf_chancount;
    d->chan_size = d->buf_active.buf_chansize;
    d->buf_base = d->buf_active.buf_ptr;

}

static void 
alloc(mfp_processor * proc, void * alloc_data) 
{
    buf_info * buf = (buf_info *)alloc_data;

    if (buf->buf_type == BUFTYPE_SHARED) {
        shared_buffer_alloc(buf);
    }
    else {
        /* private buffer alloc, not shared with other processes */
        int allocsize = buf->buf_chancount * buf->buf_chansize * sizeof(float);
        buf->buf_size = allocsize;
        buf->buf_ptr = g_malloc0(allocsize);
    }   
}


static int
config(mfp_processor * proc) 
{
    gpointer size_ptr = g_hash_table_lookup(proc->params, "size");
    gpointer channels_ptr = g_hash_table_lookup(proc->params, "channels");

    gpointer recenable_ptr = g_hash_table_lookup(proc->params, "rec_enabled");
    gpointer recchan_ptr = g_hash_table_lookup(proc->params, "rec_channels");
    gpointer trigchan_ptr = g_hash_table_lookup(proc->params, "trig_chan");
    gpointer trigthresh_ptr = g_hash_table_lookup(proc->params, "trig_thresh");

    gpointer bufmode_ptr = g_hash_table_lookup(proc->params, "buf_mode");
    gpointer bufstate_ptr = g_hash_table_lookup(proc->params, "buf_state");
    gpointer playchan_ptr = g_hash_table_lookup(proc->params, "play_channels");

    gpointer regionstart_ptr = g_hash_table_lookup(proc->params, "region_start");
    gpointer regionend_ptr = g_hash_table_lookup(proc->params, "region_end");

    gpointer clearchan_ptr = g_hash_table_lookup(proc->params, "clear_channels");

    builtin_buffer_data * d = (builtin_buffer_data *)(proc->data);

    int new_size=d->chan_size, new_channels=d->chan_count;

    int config_handled = 1; 

    if(size_ptr != NULL) {
        new_size = (int)(*(float *)size_ptr);
    }
    if(channels_ptr != NULL) {
        new_channels = (int)(*(float *)channels_ptr);
    }

    if ((new_size != d->chan_size) || (new_channels != d->chan_count)) {
        if(d->buf_to_alloc.buf_ready == ALLOC_READY) {
            buffer_activate(d);
            d->region_start = 0;
            d->region_end = 0; 
            d->buf_pos = 0;
            if (d->buf_active.buf_type == BUFTYPE_SHARED) {
                mfp_dsp_send_response_str(proc, RESP_BUFID, d->buf_active.shm_id);
                mfp_dsp_send_response_int(proc, RESP_BUFSIZE, d->buf_active.buf_chansize);
                mfp_dsp_send_response_int(proc, RESP_BUFCHAN, d->buf_active.buf_chancount);
                mfp_dsp_send_response_int(proc, RESP_RATE, mfp_samplerate);
                mfp_dsp_send_response_bool(proc, RESP_BUFRDY, 1);
            }
        }
        else if (d->buf_to_alloc.buf_ready == ALLOC_IDLE) {
            d->buf_to_alloc.shm_fd = -1;
            d->buf_to_alloc.shm_id[0] = 0;
            d->buf_to_alloc.buf_type = d->buf_active.buf_type;
            d->buf_to_alloc.buf_ptr = NULL;
            d->buf_to_alloc.buf_chancount = new_channels;
            d->buf_to_alloc.buf_chansize = new_size;

            mfp_alloc_allocate(proc, &d->buf_to_alloc, &(d->buf_to_alloc.buf_ready));
            config_handled = 0;
        }
        else {
            /* still working */ 
            config_handled = 0;
        }
    }

    if (bufmode_ptr != NULL) {
        d->buf_mode = *(float *)bufmode_ptr;
    }

    if (bufstate_ptr != NULL) {
        if ((*(float *)bufstate_ptr) > 0.5) {
            d->buf_state = BUF_ACTIVE;
        }
        else {
            d->buf_state = BUF_IDLE;
        }
        g_hash_table_remove(proc->params, "buf_state");
        g_free(bufstate_ptr);
    }

    if (recenable_ptr != NULL) {
        d->rec_enabled = (int)(*(float *)recenable_ptr);
        if(!d->rec_enabled) {
            if ((d->buf_mode == REC_LOOPSET) || (d->buf_mode == REC_LOOP)) {
                d->buf_mode = PLAY_LOOP;
            }
            else {
                d->buf_mode == PLAY_BANG;
            }
        }
    }

    if (recchan_ptr != NULL) {
        d->rec_channels = (int)(*(float *)recchan_ptr);
    }

    if (trigchan_ptr != NULL) {
        d->trig_channel = *(float *)trigchan_ptr;
    }

    if (trigthresh_ptr != NULL) {
        d->trig_thresh = *(float *)trigthresh_ptr;
    }

    if (regionstart_ptr != NULL) {
        d->region_start = (int)(*(float *)regionstart_ptr);
    }

    if (regionend_ptr != NULL) {
        d->region_end = (int)(*(float *)regionend_ptr);
    }

    if (playchan_ptr != NULL) {
        d->play_channels = (int)(*(float *)playchan_ptr);
    }
    return config_handled;
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
    p->alloc = alloc;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "buf_id", (gpointer)PARAMTYPE_STRING);
    g_hash_table_insert(p->params, "channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "size", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "buf_mode", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "buf_state", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_enabled", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_chan", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_op", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_thresh", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "region_start", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "region_end", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "play_channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clear_channels", (gpointer)PARAMTYPE_FLT);


    return p;
}


