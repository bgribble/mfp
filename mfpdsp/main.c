
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

/* main() gets called only if this is a standalone JACK client 
 * startup.  The MFP process will cause this to be run */ 
int
main(int argc, char ** argv) 
{
    char * sockname;
    char default_sockname[] = MFP_DEFAULT_SOCKET; 

    if (argc < 2) {
        printf("mfpdsp:main() No socket specified, using default\n");
        sockname = default_sockname;
    }
    else {
        sockname = argv[1];
    }
    printf("mfpdsp:main() Starting up as standalone JACK client\n");
  
    /* set up global state */
    mfp_dsp_init();
    mfp_alloc_init();
    mfp_comm_init(argv[1]);

    /* enter main lister loop */ 
    printf("mfpdsp:main() Entering comm event loop, will not return to main()\n");
    mfp_comm_io_start();
    mfp_comm_io_wait();

    printf("mfpdsp:main() Returned from comm event loop, will exit.\n"); 
    return 0;

}


