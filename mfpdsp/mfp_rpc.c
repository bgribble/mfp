#include "mfp_dsp.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <glib.h>
#include <json-glib/json-glib.h>


char * 
mfp_rpc_json_build(mfp_respdata r)
{
    const char tmpl[] = "{ \"jsonrpc\": \"2.0\", \"method\": \"response\", "
        "\"params\": { \"rpcid\": %d, \"resp_type\": %d, \"resp_value\": %s }}";
    char tbuf[MFP_MAX_MSGSIZE];

    char * msgbuf = g_alloc0(MFP_MAX_MSGSIZE * sizeof(char));

    switch(r.response_type) {
        case PARAMTYPE_FLT:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "%f", r.response.f);
            break;
        case PARAMTYPE_BOOL:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "%d", r.response.i);
            break;
        case PARAMTYPE_INT:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "%d", r.response.i);
            break;
        case PARAMTYPE_STRING:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "\"%s\"", r.response.c);
            g_free(r.response.c);
            break;
    }
    snprintf(msgbuf, MFP_MAX_MSGSIZE-1, tmpl, r.dst_proc, r.response_type, tbuf);
    return msgbuf;
}

int 
mfp_rpc_json_dispatch(const char * msgbuf, int msglen) 
{

}

