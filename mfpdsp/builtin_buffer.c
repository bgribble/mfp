
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
    
    /* trigger settings (for TRIG_THRESH, TRIG_EXT modes */ 
    int trig_pretrigger;
    int trig_channel;
    int trig_op;
    mfp_sample trig_thresh;

    /* record settings */ 
    int rec_mode;
    int rec_state;
    int rec_channels;
    int rec_enabled;
    int rec_pos;

    /* play settings */ 
    int play_mode; 
    int play_state;
    int play_channels;
    int play_pos;

    /* region definition (for LOOP modes) */ 
    int region_start;
    int region_end; 

} buf_info;

/* rec_mode values */ 
#define REC_BANG 0    /* on Bang, record buffer and stop */ 
#define REC_LOOP 1    /* continuously record between region_start and region_end */ 
#define REC_LOOPSOS 2 /* record in region, adding to previous contents */ 
#define TRIG_THRESH 3 /* When trig_channel crosses trig_thresh, rec buffer and stop */ 
#define TRIG_EXT 4    /* when external input crosses trig_thresh, rec buffer and stop */ 

/* play_mode values */
#define PLAY_TRIG 0   /* output following record state */ 
#define PLAY_LOOP 1   /* loop over region */ 

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

/* play_state values */ 
#define PLAY_IDLE 0 
#define PLAY_ACTIVE 1
#define REC_IDLE 0 
#define REC_ACTIVE 1 

static void 
init(mfp_processor * proc) 
{
    buf_info * d = g_malloc0(sizeof(buf_info));

    d->shm_id[0] = 0;
    d->shm_fd = -1;
    d->shm_size = 0;
    d->shm_ptr = NULL;
    d->chan_count = 0;
    d->chan_size = 0;
    d->trig_channel = 0;
    d->trig_pretrigger = 0;
    d->trig_op = TRIG_GT;
    d->trig_thresh = 0.0;
    
    d->rec_mode = REC_BANG;
    d->rec_state = REC_IDLE;
    d->rec_enabled = 0;
    d->rec_channels = 0;
    d->rec_pos = 0;

    d->play_mode = PLAY_TRIG;
    d->play_state = PLAY_IDLE; 
    d->play_channels = 0;
    d->play_pos = 0;

    d->region_start = 0;
    d->region_end = 0;
    
    proc->data = d;

    return;
}

static int 
process(mfp_processor * proc) 
{
    buf_info * d = (buf_info *)(proc->data);
    int dstart = 0;
    int channel, tocopy;
    mfp_block * trig_block;
    mfp_sample * outptr, *inptr;
    int inpos, outpos;
    int loopstart=0; 

    /* if not currently capturing, check for trigger conditions */ 
    if(d->rec_state == REC_IDLE && d->rec_enabled) {
        if ((d->rec_mode == TRIG_EXT) || (d->rec_mode == TRIG_THRESH)) {
            /* trig_block is the data we will be looking at to find a trigger condition */
            switch (d->rec_mode) {
                case TRIG_EXT: 
                    trig_block = proc->inlet_buf[proc->inlet_conn->len - 1];
                    break;

                case TRIG_THRESH:
                    if(d->trig_channel > proc->inlet_conn->len-1) 
                        return -1;
                    trig_block = proc->inlet_buf[d->trig_channel];
                    break;
            }

            /* iterate over trig_block looking for a trigger */ 
            dstart = 0;
            while(d->rec_state == 0) {
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
                        d->rec_state = REC_ACTIVE;
                        d->trig_pretrigger = 0;
                    }
                    else if ((d->trig_op == TRIG_LT)  
                        && (trig_block->data[dstart] < d->trig_thresh)) {
                        d->rec_state = REC_ACTIVE;
                        d->trig_pretrigger = 0;
                    }
                }
                if(d->rec_state == REC_IDLE)
                    dstart++;
                if (dstart >= trig_block->blocksize)
                    break;
            }

            if (d->rec_state == REC_ACTIVE) {
                d->region_start = 0;
                d->region_end = d->chan_size;

                d->rec_pos = d->region_start;
                    
                if (d->play_mode == PLAY_TRIG) {
                    d->play_pos = d->region_start;
                    d->play_state = PLAY_ACTIVE; 
                }

                mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 1);
            }
        }
        else {
            d->rec_state = REC_ACTIVE;
            d->rec_pos = d->region_start; 
            loopstart = 1;
        }
    }


    /* if we are triggered, copy data from inlets to buffer */
    if(d->rec_state == REC_ACTIVE) {
        /* copy rest of the block or available space */
        if (d->rec_mode == REC_LOOPSOS) {
            tocopy = mfp_blocksize;
        }
        else {
            tocopy = MIN(mfp_blocksize-dstart, d->chan_size - d->rec_pos);
        }

        /* iterate over channels, grabbbing data if channel is active */
        for(channel=0; channel < d->chan_count; channel++) {
            if((1 << channel) & d->rec_channels) {
                if (d->rec_mode == REC_LOOPSOS) {
                    /* accumulate into buffer */ 
                    outptr = (float *)d->shm_ptr + (channel*d->chan_size) + d->rec_pos;
                    outpos = d->rec_pos;
                    inptr = proc->inlet_buf[channel]->data;
                    for (inpos = 0; inpos < tocopy; inpos++) {
                        *outptr++ += *inptr++;
                        outpos++;
                        if (outpos > d->region_end) {
                            outpos = d->region_start;
                            outptr =  (float *)d->shm_ptr + (channel*d->chan_size) + outpos;
                        }
                    }
                }
                else {
                    memcpy((float *)d->shm_ptr + (channel*d->chan_size) + d->rec_pos,
                            proc->inlet_buf[channel]->data + dstart,
                            sizeof(mfp_sample)*tocopy);
                }
            }
        }

        /* if we reached the end of the buffer, untrigger */
        switch (d->rec_mode) {
            case REC_BANG:
                d->rec_pos += tocopy;
                if(d->rec_pos >= d->region_end) {
                    d->rec_state = REC_IDLE;
                    d->rec_enabled = 0;
                    d->rec_pos = d->region_start; 
                }
                break;

            case TRIG_THRESH:
            case TRIG_EXT:
                d->rec_pos += tocopy;
                if(d->rec_pos >= d->region_end) {
                    d->rec_state = REC_IDLE;
                    d->rec_pos = d->region_start; 
                    d->trig_pretrigger = 0;
                }
                break;

            case REC_LOOP:
                d->rec_pos += tocopy;
                if (d->rec_pos > d->region_end) 
                    d->region_end = d->rec_pos;

                if(d->rec_pos >= d->chan_size) {
                    d->rec_pos = d->region_start; 
                    loopstart = 1;
                }
                break;

            case REC_LOOPSOS: 
                inpos = d->rec_pos - d->region_start; 
                d->rec_pos = (inpos + mfp_blocksize) % (d->region_end-d->region_start)
                    + d->region_start;
                if (inpos + mfp_blocksize > (d->region_end - d->region_start)) {
                    loopstart = 1;
                }

                break; 
        }


        if (d->rec_state == REC_IDLE) {
            mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 0);
        }
    }

    /* zero output buffer in any case */ 
    mfp_block_zero(proc->outlet_buf[0]);

    /* if we are playing, copy data from the buffer to the outlet */ 
    if (d->play_state != PLAY_IDLE) {
        if (d->region_end == 0) {
            return 0;
        }
        /* accumulate non-masked channels in the output buffer */ 
        for(channel=0; channel < d->chan_count; channel++) {
            if((1 << channel) & d->play_channels) {
                outptr = proc->outlet_buf[0]->data;
                inptr = (float *)(d->shm_ptr) + (channel*d->chan_size);
                inpos = d->play_pos;
                for(outpos = 0; outpos < mfp_blocksize; outpos++) {
                    if (inpos < d->region_end) {
                        *outptr++ += inptr[inpos++];
                    }
                    else if (d->play_mode != PLAY_LOOP) {
                        *outptr++ = 0;
                    }
                    else {
                        inpos = d->region_start;
                        *outptr ++ += inptr[inpos++];
                    }
                }
            } 
        }
        
        /* update d->play_pos for next block */ 
        if (d->play_pos + mfp_blocksize < d->region_end) {
            d->play_pos += mfp_blocksize;
        }
        else if (d->play_mode != PLAY_LOOP) {
            d->play_pos = d->region_start;
            d->play_state = PLAY_IDLE;
        }
        else {
            d->play_pos = 
                d->region_start + ((d->play_pos - d->region_start + mfp_blocksize) 
                                 % (d->region_end - d->region_start));
            loopstart = 1;
        }

    }
    if(loopstart > 0) {
        mfp_dsp_send_response_bool(proc, RESP_LOOPSTART, 1);
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
    d->region_start = 0;
    d->region_end = 0;
}


static void
config(mfp_processor * proc) 
{
    gpointer size_ptr = g_hash_table_lookup(proc->params, "size");
    gpointer channels_ptr = g_hash_table_lookup(proc->params, "channels");

    gpointer recmode_ptr = g_hash_table_lookup(proc->params, "rec_mode");
    gpointer recstate_ptr = g_hash_table_lookup(proc->params, "rec_state");
    gpointer recenable_ptr = g_hash_table_lookup(proc->params, "rec_enabled");
    gpointer recchan_ptr = g_hash_table_lookup(proc->params, "rec_channels");

    gpointer trigchan_ptr = g_hash_table_lookup(proc->params, "trig_chan");
    gpointer trigthresh_ptr = g_hash_table_lookup(proc->params, "trig_thresh");
    gpointer trigrept_ptr = g_hash_table_lookup(proc->params, "trig_repeat");

    gpointer playmode_ptr = g_hash_table_lookup(proc->params, "play_mode");
    gpointer playstate_ptr = g_hash_table_lookup(proc->params, "play_state");
    gpointer playchan_ptr = g_hash_table_lookup(proc->params, "play_channels");

    gpointer regionstart_ptr = g_hash_table_lookup(proc->params, "region_start");
    gpointer regionend_ptr = g_hash_table_lookup(proc->params, "region_end");

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
            d->rec_pos = 0;
            buffer_alloc(d);

            mfp_dsp_send_response_str(proc, RESP_BUFID, d->shm_id);
            mfp_dsp_send_response_int(proc, RESP_BUFSIZE, d->chan_size);
            mfp_dsp_send_response_int(proc, RESP_BUFCHAN, d->chan_count);
            mfp_dsp_send_response_int(proc, RESP_RATE, mfp_samplerate);
            mfp_dsp_send_response_bool(proc, RESP_BUFRDY, 1);
        }
    }

    if (recmode_ptr != NULL) {
        d->rec_mode = *(float *)recmode_ptr;
    }

    if (recstate_ptr != NULL) {
        if ((*(float *)recstate_ptr) > 0.5) {
            d->rec_state = 1;
        }
        else {
            d->rec_state = 0;
        }
        g_hash_table_remove(proc->params, "rec_state");
        mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, d->rec_state);
    }

    if (recenable_ptr != NULL) {
        d->rec_enabled = (int)(*(float *)recenable_ptr);
        if(!d->rec_enabled) {
            d->rec_state = REC_IDLE;
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

    if (playstate_ptr != NULL) {
        d->play_state = (int)(*(float *)playstate_ptr);
        if((d->play_state == PLAY_ACTIVE) && (d->play_pos == d->region_start)) {
            mfp_dsp_send_response_bool(proc, RESP_LOOPSTART, 1);
        }
    }
    
    if (playchan_ptr != NULL) {
        d->play_channels = (int)(*(float *)playchan_ptr);
    }
    if (playmode_ptr != NULL) {
        d->play_mode = (int)(*(float *)playmode_ptr);
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
    g_hash_table_insert(p->params, "rec_mode", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_state", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_enabled", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_chan", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_op", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_thresh", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "region_start", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "region_end", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "play_channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "play_mode", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "play_state", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "play_pos", (gpointer)PARAMTYPE_FLT);

    return p;
}


