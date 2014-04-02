
#include <glib.h>
#include <jack/jack.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <execinfo.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <semaphore.h>

#include "mfp_dsp.h"



static void
sigsegv_handler(int sig, siginfo_t *si, void *unused)
{
    void * buffer[100];
    char ** strings;
    int nptrs, j;

    printf("ERROR: SIGSEGV received\n");
    nptrs = backtrace(buffer, 100);
    strings = backtrace_symbols(buffer, nptrs);

    for (j = 0; j < nptrs; j++)
        printf("      %s\n", strings[j]);

    free(strings);

    exit(-11);
}


void
mfp_init_all(char * sockname) 
{
    mfp_dsp_init();
    mfp_alloc_init();
    mfp_comm_init(sockname);
    mfp_comm_io_start();
    mfp_rpc_init();
    mfp_api_init();
    mfp_initialized = 1;
    return;
}



/* main() gets called only if this is a standalone JACK client 
 * startup.  The MFP process will cause this to be run */ 
int
main(int argc, char ** argv) 
{
    char * sockname;
    char default_sockname[] = MFP_DEFAULT_SOCKET; 
    int max_blocksize = 4096;
    int num_inputs = 2;
    int num_outputs = 2; 
    mfp_context * ctxt;

    if (argc < 2) {
        printf("mfpdsp: Warning: No socket specified, using default '%s'\n", 
                default_sockname);
        sockname = default_sockname;
    }
    else { 
        sockname = argv[1];

        if (argc < 3) {
            printf("mfpdsp: Warning: No max_blocksize specified, using default '%d'\n", 
                   max_blocksize);
        }
        else {
            max_blocksize = strtod(argv[2], NULL);
            if (argc < 4) {
                printf("mfpdsp: Warning: No num_inputs specified, using default '%d'\n", 
                       num_inputs);
            }
            else {
                num_inputs = strtod(argv[3], NULL);
                if (argc < 5) { 
                    printf("mfpdsp: Warning: No num_outputs specified, using default '%d'\n", 
                           num_outputs);
                }
                else {
                    num_outputs = strtod(argv[3], NULL);
                }
            }
        }
    }

   /* install SIGSEGV handlers */
    struct sigaction sa;
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = sigsegv_handler;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) {
        printf("mfpdsp: ERROR: could not install SIGSEGV handler, exiting\n");
        return -1;
    }
    

    printf("mfpdsp: Starting up as standalone JACK client\n");
  
    /* set up global state */
    mfp_init_all(sockname);
    ctxt = mfp_jack_startup("mfpdsp", num_inputs, num_outputs);
    mfp_comm_io_wait();

    printf("mfpdsp: Returned from comm event loop, will exit.\n"); 
    return 0;

}


