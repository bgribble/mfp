#include <stdlib.h>
#include <stdio.h>
#include <dlfcn.h>

#include "lv2/atom/atom.h"
#include "lv2/atom/util.h"
#include "lv2/midi/midi.h"
#include "lv2/urid/urid.h"
#include "lv2/core/lv2.h"
#include "lv2/core/lv2_util.h"
#include "lv2/time/time.h"

#include "mfp_dsp.h"

#define MFP_LV2_URL "http://www.billgribble.com/mfp/mfp_lv2"

void *
mfp_lv2_get_port_data(mfp_lv2_info * self, int port)
{
    return g_array_index(self->port_data, void *, port);
}

/*
 * static functions for LV2 descriptor
 */


static void
mfp_lv2_handle_context_msg(mfp_context * context, int port, int64_t message) {
    mfp_lv2_info * self = context->info.lv2;
    int portnum = g_array_index(self->output_ports, int, port);
    void * outport = mfp_lv2_get_port_data(self, portnum);

    typedef struct {
        LV2_Atom_Event event;
        uint8_t        msg[3];
    } MIDIEvent;

    MIDIEvent ev;
    ev.event.body.type = self->uris.midi_MidiEvent;
    ev.event.body.size = 3;

    ev.msg[0] = (message & 0xff000000) >> 24;
    ev.msg[1] = (message & 0xff0000) >> 16;
    ev.msg[2] = (message & 0xff00) >> 8;

    lv2_atom_sequence_append_event(
        (LV2_Atom_Sequence *)outport,
        self->output_capacity,
        &ev.event
    );
}


static LV2_Handle
mfp_lv2_instantiate(
    const LV2_Descriptor * descriptor, double rate,
    const char * bundle_path, const LV2_Feature * const * features
) {
    mfp_context * context = NULL;
    mfp_lv2_info * self = NULL;

    if (!mfp_initialized) {
        mfp_init_all(NULL);
    }

    /* make sure that the MFP process is running */
    context = mfp_context_new(CTYPE_LV2);
    context->samplerate = rate;
    context->msg_handler = mfp_lv2_handle_context_msg;

    self = context->info.lv2;

    /* initializa features for MIDI event handling */
    const char * missing = lv2_features_query(
        features,
        LV2_LOG__log,  &self->logger.log, false,
        LV2_URID__map, &self->map, true,
        NULL
    );

    lv2_log_logger_set_map(&self->logger, self->map);

    if (missing) {
        lv2_log_error(&self->logger, "Missing feature <%s>\n", missing);
        free(self);
        return NULL;
    }

    self->uris.midi_MidiEvent = self->map->map(self->map->handle, LV2_MIDI__MidiEvent);
    self->uris.time_Position = self->map->map(self->map->handle, LV2_TIME__Position);
    self->uris.atom_Sequence = self->map->map(self->map->handle, LV2_ATOM__Sequence);

    self->port_symbol = g_array_new(FALSE, TRUE, sizeof(char *));
    self->port_name = g_array_new(FALSE, TRUE, sizeof(char *));
    self->port_data = g_array_new(FALSE, TRUE, sizeof(void *));
    self->port_control_values = g_array_new(FALSE, TRUE, sizeof(float));

    self->input_ports = g_array_new(FALSE, TRUE, sizeof(int));
    self->output_ports = g_array_new(FALSE, TRUE, sizeof(int));
    self->output_buffers = g_array_new(FALSE, TRUE, sizeof(mfp_block *));

    /* mfp_lv2_ttl_read populates self with info about this plugin */
    mfp_lv2_ttl_read(self, bundle_path);

    /* create output buffers */
    for(int i = 0; i < self->output_ports->len; i++) {
        mfp_block * blk = mfp_block_new(mfp_max_blocksize);
        g_array_append_val(self->output_buffers, blk);
    }

    /* request that the MFP app build this patch */
    mfp_context_init(context);

    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    int request_id = mfp_api_load_context(context, self->object_path, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
    mfp_rpc_wait(request_id);
    return (LV2_Handle)context;
}


static void
mfp_lv2_connect_port(LV2_Handle instance, uint32_t port, void * data)
{
    mfp_context * context = (mfp_context *)instance;
    mfp_lv2_info * self = context->info.lv2;

    g_array_index(self->port_data, void *, port) = data;
}

static void
mfp_lv2_activate(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance;
    mfp_lv2_info * self = context->info.lv2;
    context->activated = 1;
}

static void
mfp_lv2_send_control_input(mfp_context * context, int port, float val)
{
    int msglen = 0;
    char * msgbuf = mfp_comm_get_buffer();
    mfp_lv2_info * self = context->info.lv2;
    int port_count = 0;

    for(int i=0; i < port; i++) {
        if(self->port_input_mask & (1 << i)) {
            port_count ++;
        }
    }
    mfp_api_send_to_inlet(context, port_count, val, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

static void
mfp_lv2_send_control_output(mfp_context * context, int port, float val)
{
    int msglen = 0;
    char * msgbuf = mfp_comm_get_buffer();
    mfp_lv2_info * self = context->info.lv2;
    int port_count = 0;

    for(int i=0; i < port; i++) {
        if(self->port_output_mask & (1 << i)) {
            port_count ++;
        }
    }
    mfp_api_send_to_outlet(context, port_count, val, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

static void
mfp_lv2_send_midi_input(mfp_context * context, int port, int64_t val)
{
    int msglen = 0;
    char * msgbuf = mfp_comm_get_buffer();
    mfp_lv2_info * self = context->info.lv2;
    int port_count = 0;

    for(int i=0; i < port; i++) {
        if(self->port_input_mask & (1 << i)) {
            port_count ++;
        }
    }
    mfp_api_send_midi_to_inlet(context, port_count, val, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

static void
mfp_lv2_send_midi_output(mfp_context * context, int port, int64_t val)
{
    int msglen = 0;
    char * msgbuf = mfp_comm_get_buffer();
    mfp_lv2_info * self = context->info.lv2;
    int port_count = 0;

    for(int i=0; i < port; i++) {
        if(self->port_output_mask & (1 << i)) {
            port_count ++;
        }
    }
    mfp_api_send_midi_to_outlet(context, port_count, val, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

static void
mfp_lv2_show_editor(mfp_context * context, int show)
{
    int msglen = 0;
    char * msgbuf = mfp_comm_get_buffer();
    mfp_api_show_editor(context, show, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}


static void
mfp_lv2_run(LV2_Handle instance, uint32_t nframes)
{
    mfp_context * context = (mfp_context *)instance;
    if (context == NULL) {
        mfp_log_error("mfp_lv2_run: context is NULL");
        return;
    }
    else if (!context->activated) {
        return;
    }

    mfp_lv2_info * lv2_info = context->info.lv2;
    int first_run=1;

    mfp_dsp_set_blocksize(context, nframes);

    if (lv2_info->port_control_values->len > 0) {
        first_run = 0;
    }
    else {
        g_array_set_size(lv2_info->port_control_values, lv2_info->port_data->len);
    }

    /* send an event to control [inlet]/[outlet] on startup and any change
     * in value
     */

    for(int i=0; i < lv2_info->port_data->len; i++) {
        if (
            lv2_info->port_input_mask &
            lv2_info->port_control_mask & (1 << i)
        ) {
            int val_changed = 1;
            void * pdata = mfp_lv2_get_port_data(lv2_info, i);
            if (pdata != NULL) {
                float val = *(float *)pdata;
                if (!first_run &&
                    (g_array_index(lv2_info->port_control_values, float, i) == val )) {
                    val_changed = 0;
                }

                if (val_changed) {
                    g_array_index(lv2_info->port_control_values, float, i) = val;
                    if (i < lv2_info->port_data->len-1) {
                        mfp_lv2_send_control_input(context, i, val);
                    }
                    else {
                        mfp_lv2_show_editor(context, (int)val);
                    }
                }
            }
        }
        else if (
            lv2_info->port_input_mask &
            lv2_info->port_midi_mask & (1 << i)
        ) {
            /* this is a MIDI event which needs this LV2 magique */
            void * pdata = mfp_lv2_get_port_data(lv2_info, i);
            int64_t val = 0;
            if (pdata != NULL) {
                LV2_Atom_Sequence * inport = (LV2_Atom_Sequence *)pdata;
                LV2_ATOM_SEQUENCE_FOREACH (inport, ev) {
                    if (ev->body.type == lv2_info->uris.midi_MidiEvent) {
                        const uint8_t * const msg = (const uint8_t *)(ev + 1);
                        val = (
                            (((unsigned int)msg[0]) << 24)
                            | (((unsigned int)msg[1]) << 16)
                            | (((unsigned int)msg[2]) << 8)
                            | ((unsigned int)msg[3])
                        );
                    }
                    mfp_lv2_send_midi_input(context, i, val);
                }
            }
        }
        /* clear messages from outbound MIDI ports */
        else if (
            lv2_info->port_output_mask &
            lv2_info->port_midi_mask & (1 << i)
        ) {
            void * pdata = mfp_lv2_get_port_data(lv2_info, i);
            lv2_info->output_capacity = ((LV2_Atom_Sequence *)pdata)->atom.size;
            lv2_atom_sequence_clear((LV2_Atom_Sequence *)pdata);
            ((LV2_Atom_Sequence *)pdata)->atom.type = lv2_info->uris.atom_Sequence;
        }

    }

    mfp_dsp_run(context);

    /* copy the audio buffers to the output ports */
    for (int port = 0; port < lv2_info->output_ports->len; port ++) {
        int lv2port = g_array_index(lv2_info->output_ports, int, port);
        if (
            lv2_info->port_audio_mask &
            lv2_info->port_output_mask & (1 << lv2port)
        ) {
            mfp_sample * destptr = mfp_lv2_get_port_data(lv2_info, lv2port);
            mfp_sample * srcptr = mfp_get_output_buffer(context, port);
            memcpy(destptr, srcptr, nframes*sizeof(mfp_sample));
        }

    }
}

static void
mfp_lv2_deactivate(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance;
    mfp_lv2_info * self = context->info.lv2;
    context->activated = 0;
}

static void
mfp_lv2_cleanup(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance;
    mfp_lv2_info * self = context->info.lv2;

    mfp_context_destroy(context);
}

static const void *
mfp_lv2_extension_data(const char * uri)
{
    return NULL;
}

static char *
find_plugname(const char * fullpath)
{
    char * pdup = g_strdup(fullpath);
    char * pname;
    int plen = strlen(pdup);

    if (plen == 0) {
        return NULL;
    }
    if (pdup[plen-1] == '/') {
        pdup[plen-1] = 0;
        plen --;
    }

    pname = rindex(pdup, (int)'/');
    if (pname == NULL) {
        return NULL;
    }
    else {
        return pname+1;
    }
}


static LV2_Descriptor descriptor = {
    NULL,
    mfp_lv2_instantiate,
    mfp_lv2_connect_port,
    mfp_lv2_activate,
    mfp_lv2_run,
    mfp_lv2_deactivate,
    mfp_lv2_cleanup,
    mfp_lv2_extension_data
};

static const LV2_Descriptor *
mfp_lv2_lib_get_plugin(LV2_Lib_Handle handle, uint32_t index)
{
    char * uri = g_malloc0(2048);

    snprintf(uri, 2047, "http://www.billgribble.com/mfp/%s",
             find_plugname((const char *)handle));

    descriptor.URI = uri;

    switch (index) {
        case 0:
            return &descriptor;
        default:
            return NULL;
    }
}
static void
mfp_lv2_lib_cleanup(LV2_Lib_Handle handle)
{
    return;
}

const LV2_Lib_Descriptor *
lv2_lib_descriptor(const char * bundle_path, const LV2_Feature * const * features)
{
    LV2_Lib_Descriptor * ld = g_malloc0(sizeof(LV2_Lib_Descriptor));
    ld->handle = g_strdup(bundle_path);
    ld->size = sizeof(LV2_Lib_Descriptor);
    ld->cleanup = mfp_lv2_lib_cleanup;
    ld->get_plugin = mfp_lv2_lib_get_plugin;
    return ld;
}
