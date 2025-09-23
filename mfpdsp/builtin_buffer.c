/*
 * builtin_buffer.c -- shared-memory audio buffer player/recorder
 *
 * Copyright (c) Bill Gribble <grib@billgribble.com>
 */

#include <math.h>
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
    int trig_message;
    int trig_triggered_samples;
    int trig_xfade_samples;
    int trig_channel;
    int trig_op;
    int trig_debounce;
    int trig_xfade;
    mfp_sample trig_thresh;

    /* record settings */
    int play_channels;
    int rec_channels;
    int rec_enabled;
    int rec_latency_comp;
    int rec_overdub;

    /* region definition (for LOOP modes, set by REC_LOOPSET) */
    int region_start;
    int region_end;

    int buf_read_pos;
    int buf_write_pos;
    int buf_xfade_pos;
    int buf_mode;
    int buf_state;
    int buf_state_start_block;
    int buf_state_start_pos;

} builtin_buffer_data;

/* buf_type values */
#define BUFTYPE_PRIVATE 0
#define BUFTYPE_SHARED 1

/* buf_mode values */
#define REC_BANG 0         /* on Bang, record buffer and stop */
#define REC_LOOPSET 1      /* record, establishing region_start and region_end */
#define REC_LOOP 2         /* continuously record between region_start and region_end */
#define REC_TRIG_THRESH 3  /* When trig_channel crosses trig_thresh, rec buffer and stop */
#define REC_TRIG_EXT 4     /* when external input crosses trig_thresh, rec buffer and stop */
#define PLAY_BANG 5        /* play buffer once */
#define PLAY_LOOP 6        /* loop over region */
#define PLAY_TRIG_THRESH 7 /* When trig_channel crosses trig_thresh, play buffer to end */

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
#define BUF_PRETRIGGERED 1
#define BUF_TRIGGERED 2
#define BUF_DEBOUNCED 3
#define BUF_PRE_RETRIGGERED 4
#define BUF_XFADE 5


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

    d->trig_triggered_samples = 0;
    d->trig_xfade_samples = 0;
    d->trig_message = 0;
    d->trig_channel = 0;
    d->trig_debounce = 20;
    d->trig_xfade = 20;
    d->trig_op = TRIG_GT;
    d->trig_thresh = 0.0;

    d->rec_enabled = 0;
    d->rec_channels = 0;
    d->rec_latency_comp = 0;
    d->rec_overdub = 0;
    d->play_channels = 0;

    d->buf_read_pos = 0;
    d->buf_write_pos = 0;
    d->buf_xfade_pos = 0;
    d->buf_mode = REC_BANG;
    d->buf_state = BUF_IDLE;

    d->region_start = 0;
    d->region_end = 0;

    proc->data = d;

    return;
}

static int block_num = 0;

static double
residue(double x, double y) {
    double m = fmod(x, y);
    if (m < 0) {
        return m + y;
    }
    return m;
}


static int
calc_write_pos(builtin_buffer_data * d, int read_pos) {
    if (d->rec_latency_comp && d->play_channels) {
        int region_size = d->region_end - d->region_start;
        if (region_size > 0) {
            return d->region_start + residue(
                read_pos - (mfp_in_latency + mfp_out_latency), region_size
            );
        }
    }
    return read_pos;
}



static int
process(mfp_processor * proc)
{
    builtin_buffer_data * d = (builtin_buffer_data *)(proc->data);
    int tocopy=0;
    mfp_block * trig_block = NULL;
    mfp_sample * outptr, * inptr, * trigptr;
    int buf_triggerable = 0;
    int inpos, outpos;
    int loopstart=0;

    int total_to_proc = 0;
    int section_size = 0;
    int section_start = 0;
    int section_end = 0;
    int section_state = d->buf_state;

    if (d->buf_base == NULL) {
        return 0;
    }

    /* buf_mode will only change in config(), so it's constant
     * for this block */
    if (
        d->buf_mode == REC_TRIG_EXT
        || d->buf_mode == REC_LOOP
        || d->buf_mode == REC_LOOPSET
        || (d->buf_mode == REC_TRIG_THRESH)
        || (d->buf_mode == PLAY_BANG)
        || (d->buf_mode == PLAY_LOOP)
        || (d->buf_mode == PLAY_TRIG_THRESH)
    ) {
        buf_triggerable = 1;
    }

    /* find the block for the trigger channel, if any */
    if (
        (d->buf_mode == REC_TRIG_EXT)
        || (d->buf_mode == REC_TRIG_THRESH)
        || (d->buf_mode == PLAY_TRIG_THRESH)
    ) {
        /* trig_block is the data we will be looking at to find a trigger condition */
        switch (d->buf_mode) {
            /* I think this is historical and could be dropped? I guess it leaves
             * open the chance of having 2 separate signal sources for triggering?
             * in any case what it does is look at the last input channel for trigger */
            case REC_TRIG_EXT:
                trig_block = proc->inlet_buf[proc->inlet_conn->len - 1];
                trigptr = trig_block->data;
                break;

            /* this one looks at any specified channel for the trigger */
            case REC_TRIG_THRESH:
            case PLAY_TRIG_THRESH:
                if(d->trig_channel > (proc->inlet_conn->len-1)) {
                    return -1;
                }
                trig_block = proc->inlet_buf[d->trig_channel];
                trigptr = trig_block->data;

                break;
        }
    }

    /* zero output buffer in preparation for PLAY operations */
    for(int channel=0; channel < d->chan_count; channel++) {
        mfp_block_zero(proc->outlet_buf[channel]);
    }

    /* outer loop: repeat 2 phases:
     * 1. Look at the trigger channel to find the end of the current
     *    state block
     * 2. Iterate over channels to process between start and end-of-state */
    total_to_proc = proc->inlet_buf[0]->blocksize;
    while (buf_triggerable && (section_start < total_to_proc)) {
        section_size = 0;

        /* phase 1 -- find how far the current triggering section runs */
        int next_state = section_state;
        int region_end = d->region_end;
        int region_set = (d->region_start != 0) || (d->region_end != 0);
        int overdub = d->rec_overdub;

        if (!region_end) {
            region_end = d->buf_active.buf_size - 1;
        }

        if (trig_block) {
            for(section_size=0; section_size < total_to_proc - section_start; section_size++) {
                switch (section_state) {
                    case BUF_IDLE:
                        if((d->trig_op == TRIG_GT) && (*trigptr <= d->trig_thresh)) {
                            next_state = BUF_PRETRIGGERED;
                        }
                        else if ((d->trig_op == TRIG_LT) && (*trigptr >= d->trig_thresh)) {
                            next_state = BUF_PRETRIGGERED;
                        }
                        else if (d->trig_message) {
                            next_state = BUF_TRIGGERED;
                        }
                        else if (d->buf_mode == REC_LOOP) {
                            next_state = BUF_TRIGGERED;
                            d->buf_read_pos = MAX(0, d->region_start);
                            d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);

                            loopstart = 1;
                        }
                        else if (d->buf_mode == REC_LOOPSET) {
                            next_state = BUF_TRIGGERED;
                            d->region_start = 0;
                            d->region_end = 0;
                            d->buf_read_pos = 0;
                            d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                            loopstart = 1;
                        }
                        break;

                    case BUF_PRETRIGGERED:
                        if ((d->trig_op == TRIG_GT) && (*trigptr > d->trig_thresh)) {
                            next_state = BUF_TRIGGERED;
                            d->trig_triggered_samples = 0;
                            d->buf_read_pos = MAX(0, d->region_start);
                            d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                        }
                        else if ((d->trig_op == TRIG_LT) && (*trigptr < d->trig_thresh)) {
                            next_state = BUF_TRIGGERED;
                            d->trig_triggered_samples = 0;
                            d->buf_read_pos = MAX(0, d->region_start);
                            d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                        }
                        else if (d->trig_message) {
                            next_state = BUF_TRIGGERED;
                        }
                        break;

                    case BUF_TRIGGERED:
                        /* idle when end of region or end of buffer is reached */
                        if (d->buf_mode == REC_LOOPSET) {
                            d->region_end ++;
                        }
                        else if ((d->buf_mode == REC_LOOP) && (d->buf_read_pos + section_size >= region_end)) {
                            /* do nothing */
                        }
                        else if (d->buf_read_pos + section_size >= region_end) {
                            next_state = BUF_IDLE;
                        }
                        else if (d->trig_triggered_samples >= d->trig_debounce) {
                            next_state = BUF_DEBOUNCED;
                        }
                        d->trig_triggered_samples ++;
                        break;

                    case BUF_DEBOUNCED:
                        if (d->buf_read_pos + section_size >= region_end) {
                            next_state = BUF_IDLE;
                        }
                        else if((d->trig_op == TRIG_GT) && (*trigptr <= d->trig_thresh)) {
                            d->trig_triggered_samples ++;
                            next_state = BUF_PRE_RETRIGGERED;
                        }
                        else if((d->trig_op == TRIG_LT) && (*trigptr >= d->trig_thresh)) {
                            d->trig_triggered_samples ++;
                            next_state = BUF_PRE_RETRIGGERED;
                        }
                        else if (d->trig_message) {
                            next_state = BUF_XFADE;
                        }
                        break;

                    case BUF_PRE_RETRIGGERED:
                        if (d->buf_read_pos + section_size >= region_end) {
                            next_state = BUF_IDLE;
                        }
                        else if((d->trig_op == TRIG_GT) && (*trigptr > d->trig_thresh)) {
                            next_state = BUF_XFADE;
                            d->trig_triggered_samples = 0;
                            d->buf_xfade_pos = d->buf_read_pos + section_size;
                        }
                        else if ((d->trig_op == TRIG_LT) && (*trigptr < d->trig_thresh)) {
                            next_state = BUF_XFADE;
                            d->trig_triggered_samples = 0;
                            d->buf_xfade_pos = d->buf_read_pos + section_size;
                        }
                        break;

                    case BUF_XFADE:
                        if (d->buf_read_pos + section_size >= region_end) {
                            next_state = BUF_IDLE;
                        }
                        else if (d->trig_xfade_samples >= d->trig_xfade) {
                            next_state = BUF_DEBOUNCED;
                        }
                        d->trig_triggered_samples ++;

                        break;
                }

                if (section_state != next_state) {
                    /* set up for the action we are going to take in the next phase */
                    /* exit the trigger block iteration */
                    d->buf_state_start_block = block_num;
                    d->buf_state_start_pos = section_start + section_size;
                    break;
                }
                else {
                    /* advance trigger data pointer */
                    trigptr++;
                }

            }  /* for each sample in trigger block */
        }

        /* no trigger block means that only config messages change state */
        else {
            section_size = total_to_proc;

            switch (section_state) {
                case BUF_IDLE:
                    if (d->trig_message) {
                        next_state = BUF_TRIGGERED;
                        d->buf_read_pos = MAX(0, d->region_start);
                        d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                        section_size = 0;
                    }
                    else if (d->buf_mode == REC_LOOP) {
                        next_state = BUF_TRIGGERED;
                        section_size = 0;
                    }
                    else if (d->buf_mode == PLAY_LOOP) {
                        next_state = BUF_TRIGGERED;
                        section_size = 0;
                    }
                    else if (d->buf_mode == REC_LOOPSET) {
                        next_state = BUF_TRIGGERED;
                        d->region_start = 0;
                        d->region_end = 0;
                        d->buf_read_pos = 0;
                        d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                        loopstart = 1;
                        section_size = 0;
                    }
                    break;

                case BUF_TRIGGERED:
                    next_state = BUF_DEBOUNCED;
                    section_size = 0;
                    break;

                case BUF_DEBOUNCED:
                    if (d->trig_message) {
                        next_state = BUF_XFADE;
                        d->buf_xfade_pos = d->buf_read_pos;
                        d->buf_read_pos = MAX(0, d->region_start);
                        d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                        section_size = 0;
                    }
                    else if (d->buf_mode == REC_LOOPSET) {
                        /* stay in this mode until we reach end of buffer
                         * or the mode is changed */
                        section_size = MIN(
                            section_size,
                            d->buf_active.buf_size - d->buf_read_pos
                        );
                        d->trig_triggered_samples += section_size;
                        d->region_end += section_size;
                    }
                    else if ((d->buf_mode == REC_LOOP) || (d->buf_mode == PLAY_LOOP)) {
                        /* start and end should be set, so just stay
                         * in this mode. wraparound happens later. */
                        d->trig_triggered_samples += section_size;
                    }
                    else if ((d->buf_read_pos + section_size >= MIN(region_end, d->buf_active.buf_size))) {
                        /* "roll to end and stop" modes running into end */
                        section_size = MIN(
                            section_size,
                            MIN(region_end, d->buf_active.buf_size) - d->buf_read_pos
                        );
                        d->trig_triggered_samples += section_size;
                        next_state = BUF_IDLE;
                    }
                    else {
                        /* "roll to end and stop" modes not at end yet */
                        d->trig_triggered_samples += section_size;
                    }
                    break;

                case BUF_XFADE:
                    if (d->trig_xfade_samples + section_size >= d->trig_xfade) {
                        section_size = d->trig_xfade - d->trig_xfade_samples;
                        next_state = BUF_DEBOUNCED;
                    }
                    d->trig_triggered_samples += section_size;
                    d->trig_xfade_samples += section_size;
                    break;

                case BUF_PRETRIGGERED:
                case BUF_PRE_RETRIGGERED:
                    /* impossible states with no trigger signal */
                    d->buf_state = BUF_IDLE;
                    break;
            }
            d->trig_message = 0;

            if (section_state != next_state) {
                /* set up for the action we are going to take in the next phase */
                /* exit the trigger block iteration */
                d->buf_state_start_block = block_num;
                d->buf_state_start_pos = section_start + section_size;
            }
        }

        /* phase 2 -- move data to/from buffer and input/output */
        if (
            (section_state == BUF_IDLE)
            || (section_state == BUF_PRETRIGGERED)
        ) {
            /* ??? */
        }
        else if (
            (section_state == BUF_TRIGGERED)
            || (section_state == BUF_DEBOUNCED)
            || (section_state == BUF_PRE_RETRIGGERED)
            || (section_state == BUF_XFADE)
        ) {
            /* the block pos where we will have to wrap or otherwise stop iterating */
            int buf_fence = MIN(
                section_size,
                MIN(
                    d->chan_size - d->buf_read_pos,
                    ((region_end > d->region_start) ? (region_end - d->buf_read_pos) : d->chan_size)
                )
            );

            /* loop over channels */
            for(int channel=0; channel < d->chan_count; channel++) {
                /* if channel is in play set, copy data from buffer to outbuf */
                if((1 << channel) & d->play_channels) {
                    outptr = proc->outlet_buf[channel]->data;
                    inptr = (float *)(d->buf_base) + (channel*d->chan_size);
                    inpos = d->buf_read_pos;
                    for(outpos = section_start; outpos < section_start + section_size; outpos++) {
                        if (inpos < (d->buf_read_pos + buf_fence)) {
                            // normal condition -- playing a region
                            outptr[outpos] = inptr[inpos++];
                        }
                        else if ((d->buf_mode == PLAY_LOOP) || (d->buf_mode == REC_LOOP)) {
                            // wraparound -- reset inptr to start of region
                            if (d->region_start > region_end) {
                                inpos = 0;
                            }
                            else {
                                inpos = d->region_start;
                            }
                            outptr[outpos] = inptr[inpos++];
                        }
                        else {
                            // shouldn't get here
                            outptr[outpos] = 0;
                        }
                    }
                }

                /* if channel is in record set, copy data from inbuf to buffer */
                if(d->rec_enabled && ((1 << channel) & d->rec_channels)) {
                    /* either copy or accumulate into buffer */
                    outptr = (float *)d->buf_base + (channel*d->chan_size);
                    outpos = d->buf_write_pos;
                    inptr = proc->inlet_buf[channel]->data;
                    for (inpos = section_start; inpos < section_start + section_size; inpos++) {
                        if (outpos < (d->buf_write_pos + buf_fence)) {
                            // do nothing
                        }
                        else if (d->region_start > region_end) {
                            outpos = 0;
                        }
                        else {
                            outpos = d->region_start;
                        }
                        if (overdub) {
                            outptr[outpos++] += inptr[inpos];
                        }
                        else {
                            outptr[outpos++] = inptr[inpos];
                        }
                    }
                }

            }

            /* now advance d->buf_read_pos and d->buf_write_pos */
            int buf_remainder = (d->buf_read_pos + section_size) % (region_end - d->region_start);
            d->buf_read_pos = d->region_start + buf_remainder;
            d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
        }

        /* for XFADE, mix in the same size chunk from alsewhere in the buffer */
        if (section_state == BUF_XFADE && d->trig_xfade) {
            /* linear ramp down on old audio, we are just trying to prevent clicks */
            double ramp_step = 1.0 / (double)(d->trig_xfade);
            double ramp_start = 1.0 - (ramp_step * d->trig_xfade_samples);
            /* loop over channels */
            for(int channel=0; channel < d->chan_count; channel++) {
                /* if channel is in play set, copy data from buffer to outbuf */
                if((1 << channel) & d->play_channels) {
                    double ramp_gain = ramp_start;
                    outptr = proc->outlet_buf[channel]->data;
                    inptr = (float *)(d->buf_base) + (channel*d->chan_size);
                    inpos = d->buf_xfade_pos;
                    for(outpos = section_start; outpos < section_start + section_size; outpos++) {
                        if ((inpos <= region_end) || (d->buf_mode == PLAY_BANG)) {
                            outptr[outpos] += ramp_gain * inptr[inpos++];
                        }
                        else if ((d->buf_mode == PLAY_LOOP) || (d->buf_mode == REC_LOOP)) {
                            inpos = d->region_start;
                            outptr[outpos] += ramp_gain * inptr[inpos++];
                        }
                        else {
                            outptr[outpos] = 0;
                        }
                        ramp_gain = MAX(0.0, ramp_gain - ramp_step);
                        if (ramp_gain < .00001) {
                            break;
                        }
                    }
                }
            }
            d->trig_xfade_samples += MIN(section_size, d->trig_xfade - d->trig_xfade_samples);
        }

        /* phase 3 -- write back state to save for next block, emit any DSP responses */
        if (section_state != next_state) {
            if (loopstart) {
                mfp_dsp_send_response_bool(proc, RESP_LOOPSTART, 1);
            }
            else if (next_state == BUF_XFADE) {
                d->buf_read_pos = MAX(0, d->region_start);
                d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                d->trig_xfade_samples = 0;
                mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 1);
            }
            else if (next_state == BUF_TRIGGERED) {
                mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 1);
            }
            else if (next_state == BUF_IDLE) {
                d->buf_read_pos = MAX(0, d->region_start);
                d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
                if (section_state != BUF_PRETRIGGERED) {
                    mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 0);
                }
            }

        }

        section_state = next_state;
        section_start = section_start + section_size;
    }

    d->buf_state = section_state;
    block_num ++;

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
    if (buf->shm_fd < 0) {
        mfp_log_debug("shm_open() failed... %d (%s)\n", buf->shm_fd, strerror(errno));
    }
    if(buf->buf_ptr != NULL) {
        munmap(buf->buf_ptr, buf->buf_size);
        buf->buf_ptr = NULL;
    }
    ftruncate(buf->shm_fd, size);
    buf->buf_size = size;
    buf->buf_ptr = mmap(NULL,  size, PROT_READ|PROT_WRITE, MAP_SHARED, buf->shm_fd, 0);
    if (buf->buf_ptr == NULL) {
        mfp_log_debug("mmap() failed... %d (%s)\n", buf->shm_fd, strerror(errno));
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
        int allocsize = buf->buf_chancount * buf->buf_chansize * sizeof(mfp_sample);
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
    gpointer reccomp_ptr = g_hash_table_lookup(proc->params, "rec_latency_comp");
    gpointer recoverdub_ptr = g_hash_table_lookup(proc->params, "rec_overdub");

    gpointer trigtrigger_ptr = g_hash_table_lookup(proc->params, "trig_trigger");
    gpointer trigchan_ptr = g_hash_table_lookup(proc->params, "trig_chan");
    gpointer trigthresh_ptr = g_hash_table_lookup(proc->params, "trig_thresh");
    gpointer trigdebounce_ptr = g_hash_table_lookup(proc->params, "trig_debounce");

    gpointer bufmode_ptr = g_hash_table_lookup(proc->params, "buf_mode");
    gpointer bufstate_ptr = g_hash_table_lookup(proc->params, "buf_state");
    gpointer bufpos_ptr = g_hash_table_lookup(proc->params, "buf_pos");
    gpointer playchan_ptr = g_hash_table_lookup(proc->params, "play_channels");

    gpointer regionstart_ptr = g_hash_table_lookup(proc->params, "region_start");
    gpointer regionend_ptr = g_hash_table_lookup(proc->params, "region_end");

    gpointer clearchan_ptr = g_hash_table_lookup(proc->params, "clear_channels");

    builtin_buffer_data * d = (builtin_buffer_data *)(proc->data);

    int new_size = d->chan_size;
    int new_channels = d->chan_count;

    int config_handled = 1;

    if(size_ptr != NULL) {
        new_size = (int)(*(double *)size_ptr);
    }
    if(channels_ptr != NULL) {
        new_channels = (int)(*(double *)channels_ptr);
    }

    if ((new_size != d->chan_size) || (new_channels != d->chan_count)) {
        int need_more_buffers = (
            new_channels > d->chan_count || new_size > d->chan_size
        );
        if(d->buf_to_alloc.buf_ready == ALLOC_READY) {
            buffer_activate(d);
            d->region_start = 0;
            d->region_end = 0;
            d->buf_read_pos = 0;
            d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);

            if (need_more_buffers) {
                mfp_proc_realloc_buffers(proc, d->chan_count, d->chan_count, proc->context->blocksize);
            }
            if (d->buf_active.buf_type == BUFTYPE_SHARED) {
                mfp_dsp_send_response_str(proc, RESP_BUFID, d->buf_active.shm_id);
                mfp_dsp_send_response_int(proc, RESP_BUFSIZE, d->buf_active.buf_chansize);
                mfp_dsp_send_response_int(proc, RESP_BUFCHAN, d->buf_active.buf_chancount);
                mfp_dsp_send_response_int(proc, RESP_RATE, proc->context->samplerate);
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
        d->buf_mode = *(double *)bufmode_ptr;
    }

    if (bufstate_ptr != NULL) {
        if ((*(double *)bufstate_ptr) > 0.5) {
            d->trig_message = 1;
        }
        else {
            d->buf_state = BUF_IDLE;
            d->buf_state_start_block = block_num + 1;
            d->buf_state_start_pos = 0;
        }
        g_hash_table_remove(proc->params, "buf_state");
        g_free(bufstate_ptr);
    }

    if (reccomp_ptr) {
        d->rec_latency_comp = (int)(*(double *)reccomp_ptr);
        g_hash_table_remove(proc->params, "rec_latency_comp");
    }

    if (bufpos_ptr) {
        d->buf_read_pos = (int)(*(double *)bufpos_ptr);
        d->buf_write_pos = calc_write_pos(d, d->buf_read_pos);
        g_hash_table_remove(proc->params, "buf_pos");
    }

    if (recenable_ptr != NULL) {
        d->rec_enabled = (int)(*(double *)recenable_ptr);
        if(!d->rec_enabled) {
            if ((d->buf_mode == PLAY_LOOP) || (d->buf_mode == REC_LOOPSET) || (d->buf_mode == REC_LOOP)) {
                d->buf_mode = PLAY_LOOP;
                d->trig_message = 0;
                if (trigtrigger_ptr != NULL) {
                    g_hash_table_remove(proc->params, "trig_trigger");
                }
            }
            else {
                d->buf_mode = PLAY_BANG;
                mfp_dsp_send_response_bool(proc, RESP_TRIGGERED, 1);
            }
        }
    }

    if (recchan_ptr != NULL) {
        d->rec_channels = (int)(*(double *)recchan_ptr);
    }

    if (recoverdub_ptr != NULL) {
        d->rec_overdub = (int)(*(double *)recoverdub_ptr);
    }

    if (trigchan_ptr != NULL) {
        d->trig_channel = *(double *)trigchan_ptr;
    }

    if (trigthresh_ptr != NULL) {
        d->trig_thresh = *(double *)trigthresh_ptr;
    }
    if (trigtrigger_ptr != NULL) {
        g_hash_table_remove(proc->params, "trig_trigger");
        d->trig_message = 1;
    }

    if (trigdebounce_ptr != NULL) {
        d->trig_debounce = (int)(*(double *)trigdebounce_ptr);
    }

    if (regionstart_ptr != NULL) {
        d->region_start = (int)(*(double *)regionstart_ptr);
    }

    if (regionend_ptr != NULL) {
        d->region_end = (int)(*(double *)regionend_ptr);
    }

    if (playchan_ptr != NULL) {
        d->play_channels = (int)(*(double *)playchan_ptr);
    }

    if (clearchan_ptr != NULL) {
        int channel;
        int clear_channels = (int)(*(double *)clearchan_ptr);
        for(channel = 0; channel < d->chan_count; channel++) {
            if((1 << channel) & clear_channels) {
                bzero(
                    d->buf_base + channel*d->chan_size,
                    sizeof(mfp_sample)*d->chan_size
                );
            }
        }
        g_hash_table_remove(proc->params, "clear_channels");
        g_free(clearchan_ptr);
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
    g_hash_table_insert(p->params, "buf_mode", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "buf_state", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "buf_pos", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "buf_latency_comp", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "size", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_overdub", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_enabled", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rec_channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_trigger", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_chan", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_debounce", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_xfade", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_op", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_thresh", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "region_start", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "region_end", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "play_channels", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "clear_channels", (gpointer)PARAMTYPE_FLT);


    return p;
}


