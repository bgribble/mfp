#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <glib.h>

#include <serd/serd.h>

#include "mfp_dsp.h"

/* 
 * This is a limited TTL (turtle) parser for LV2 RDF files.  It uses libserd
 * to parse the doc and collect just enough information to fire up MFP as a 
 * plugin instance. It does NOT completely grok TTL 
 *
 * The entry point is mfp_lv2_ttl_read, which is called from the LV2 plugin 
 * instantiation.  Here's the basic flow: 
 *
 * 1. LV2 host finds a saved MFP LV2 plugin def in mymfpplugin.lv2/manifest.ttl 
 * 2. LV2 host parses the .ttl file and finds that mymfpplugin is implemented 
 *    in the shared library libmfpdsp.so.  ALL saved MFP plugins are implemented in
 *    this same shared object, but have different .ttl files. 
 * 3. LV2 host does a dlopen() on mfpdsp.so and then calls lv2_descriptor() from 
 *    mfp_lv2_plug.c 
 * 4. lv2_descriptor() returns a structure including mfp_lv2_instantiate() from 
 *    mfp_lv2_plug.c as the instantiation function for mymfpplugin 
 * 5. LV2 host calls mfp_lv2_instantiate() with the "bundle_path" (.../mymfpplugin.lv2/) 
 *    as an argument 
 * 6. mfp_lv2_instantiate() calls mfp_lv2_ttl_read on the manifest.ttl within the 
 *    bundle directory. 
 *
 * At that point, the purpose of reading the TTL file is to figure out 
 * how many input and output ports to create for the plugin, which ones are 
 * audio and which are control, and what .mfp patch files to have MFP load 
 * once it gets up and running.  These are all saved by MFP in the .ttl file 
 * when "save_as_lv2" gets called. 
 *
 * This isn't a general LV2 TTL parser.  It's only intended for use by MFP to 
 * parse TTL files MFP generated. 
 */



typedef struct { 
    const SerdNode * plugin_node;
    char * current_port_name; 
    int  current_port_num;
    char * bundle_path;
    mfp_lv2_info * lv2;    
} ttl_parse_info;


static SerdStatus 
ttl_base(void * pinfo, const SerdNode * uri)
{
    return SERD_SUCCESS;
}

static SerdStatus
ttl_prefix(void * pinfo, const SerdNode * name, const SerdNode * uri)
{
    return SERD_SUCCESS;
}

static SerdStatus
ttl_statement(void * data, SerdStatementFlags flags, const SerdNode * graph, 
              const SerdNode * subject, const SerdNode * predicate, const SerdNode * object, 
              const SerdNode * object_datatype, const SerdNode * object_lang)
{
    ttl_parse_info * pinfo = data;
    char * tmpstr; 
    void * nullptr = NULL;

    /* "a lv2:Plugin" line sets the Serd root */
    if (object && object->buf && (!strcmp(object->buf, "lv2:Plugin"))) {
        printf("found lv2:Plugin\n");
        pinfo->plugin_node = subject;
    }
    else if (pinfo->plugin_node != NULL) {
        /* doap:name gives the MFP object name to be loaded */  
        if ((subject != NULL) && (subject == pinfo->plugin_node)
                && predicate && predicate->buf 
                && !strcmp(predicate->buf, "doap:name") && (object != NULL)) {
            if (!object->buf) { 
                printf("  doap:name but no object buf?\n");
            }
            printf("  found mfp object name: '%s'\n", object->buf);
            pinfo->lv2->object_name = g_strdup(object->buf);  
            pinfo->lv2->object_path = g_malloc0(strlen(object->buf) + 
                                                strlen(pinfo->bundle_path) + 1);
            sprintf(pinfo->lv2->object_path, "%s/%s", pinfo->bundle_path, 
                    object->buf);
        }

        /* lv2:port starts a port definition */ 
        if ((subject != NULL) && (subject == pinfo->plugin_node)
                && predicate && predicate->buf && (!strcmp(predicate->buf, "lv2:port"))
                && object) {
            if (pinfo->current_port_num >= 0) {
                g_free(pinfo->current_port_name);
                pinfo->current_port_name = NULL;
            }
            pinfo->current_port_name = g_strdup(object->buf);
            pinfo->current_port_num ++;
            printf("  found new port %d: '%s'\n", pinfo->current_port_num, 
                    pinfo->current_port_name);
        }
        /* lv2:InputPort is on all audio and control inputs */ 
        if (subject && subject->buf && pinfo->current_port_name
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf && (!strcmp(object->buf, "lv2:InputPort"))) {
            printf("    port %d is an input port\n", pinfo->current_port_num);
            pinfo->lv2->port_input_mask |= (0x0001 << pinfo->current_port_num);
            g_array_append_val(pinfo->lv2->input_ports, pinfo->current_port_num);
        }

        /* lv2:OutputPort is on all audio and control outputs */ 
        if (subject && subject->buf && pinfo->current_port_name 
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf && !strcmp(object->buf, "lv2:OutputPort")) {
            printf("    port %d is an output port\n", pinfo->current_port_num);
            pinfo->lv2->port_output_mask |= (0x0001 << pinfo->current_port_num);
            g_array_append_val(pinfo->lv2->output_ports, pinfo->current_port_num);
        }

        /* lv2:ControlPort is on all control ports */ 
        if (subject && subject->buf && pinfo->current_port_name 
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf && (!strcmp(object->buf, "lv2:ControlPort"))) {
            printf("    port %d is a control port\n", pinfo->current_port_num);
            pinfo->lv2->port_control_mask |= (0x0001 << pinfo->current_port_num);
        }

        /* lv2:AudioPort is on all audio ports */ 
        if (subject && subject->buf && pinfo->current_port_name 
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf && (!strcmp(object->buf, "lv2:AudioPort"))) {
            printf("    port %d is an audio port\n", pinfo->current_port_num);
            pinfo->lv2->port_audio_mask |= (0x0001 << pinfo->current_port_num);
        }

        /* lv2:MidiPort is on all MIDI ports */ 
        if (subject && subject->buf && pinfo->current_port_name 
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf && (!strcmp(object->buf, "lv2:MidiPort"))) {
            printf("    port %d is a MIDI port\n", pinfo->current_port_num);
            pinfo->lv2->port_midi_mask |= (0x0001 << pinfo->current_port_num);
        }

        /* Ports all have an lv2:symbol */ 
        if (subject && subject->buf && pinfo->current_port_name 
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf
                && predicate && predicate->buf && (!strcmp(predicate->buf, "lv2:symbol"))) {
            printf("    port %d symbol= '%s'\n", pinfo->current_port_num, object->buf);
            tmpstr = g_strdup(object->buf);
            g_array_append_val(pinfo->lv2->port_symbol, tmpstr);
            g_array_append_val(pinfo->lv2->port_data, nullptr);
        }

        /* Ports all have an lv2:name */ 
        if (subject && subject->buf && pinfo->current_port_name 
                && (!strcmp(subject->buf,  pinfo->current_port_name))
                && object && object->buf
                && predicate && predicate->buf && (!strcmp(predicate->buf, "lv2:name"))) {
            printf("    port %d name= '%s'\n", pinfo->current_port_num, object->buf);
            tmpstr = g_strdup(object->buf);
            g_array_append_val(pinfo->lv2->port_name, tmpstr);
        }
    }


    return SERD_SUCCESS;
}

static SerdStatus
ttl_end(void * pinfo, const SerdNode * end)
{
    return SERD_SUCCESS;
}



int
mfp_lv2_ttl_read(mfp_lv2_info * self, const char * bundle_path) 
{
    char mfest[] = "/manifest.ttl";
    int base_pathlen = strlen(bundle_path);
    char * combined_path = g_malloc(base_pathlen + strlen(mfest) + 1);
    FILE * fp = NULL; 
    SerdReader * reader = NULL; 
    ttl_parse_info * pinfo;

    sprintf(combined_path, "%s%s", bundle_path, mfest);
    mfp_log_debug("ttl_read: looking for file at '%s'\n", combined_path); 

    fp = fopen(combined_path, "rb");
    pinfo = g_malloc0(sizeof(ttl_parse_info));
    pinfo->current_port_num = -1;
    pinfo->bundle_path = bundle_path;
    pinfo->lv2 = self;

    reader = serd_reader_new(SERD_TURTLE, (void *)pinfo, 
                             NULL, ttl_base, ttl_prefix, ttl_statement, ttl_end); 

    serd_reader_read_file_handle(reader, fp, combined_path);

    if (pinfo->current_port_name) {
        g_free(pinfo->current_port_name);
        pinfo->current_port_name = NULL;
    }
    pinfo->lv2 = NULL;

    g_free(combined_path);
    g_free(pinfo);

    return 1;

}
