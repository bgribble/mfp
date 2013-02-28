#include <stdio.h>
#include <unistd.h>
#include <pthread.h>

#include "mfp_dsp.h"

typedef struct {
    mfp_processor * proc;
    void (* handler)(mfp_processor *, void *); 
    void * data;
    int * status;
} mfp_alloc_reqinfo;

#define REQUEST_BUFSIZE 128
#define REQUEST_LASTIND 127 

mfp_alloc_reqinfo request_queue[REQUEST_BUFSIZE];
int request_queue_read = 0;
int request_queue_write = 0;

int mfp_alloc_quit = 0; 

pthread_t mfp_alloc_thread;

int 
mfp_alloc_allocate(mfp_processor * proc, void * req_data, int * req_status)
{
    mfp_alloc_reqinfo req; 
    
    req.proc = proc;
    req.handler = proc->typeinfo->alloc; 
    req.data = req_data;
    req.status = req_status; 

    if (req.handler == NULL) {
        return 0;
    }
    
    if((request_queue_read == 0 && request_queue_write == REQUEST_LASTIND)
        || (request_queue_write + 1 == request_queue_read)) {
        *req_status = ALLOC_IDLE;
        return 0;
    }
    else {
        printf("allocate: pushing request at position %d\n", request_queue_write);
        *req_status = ALLOC_WORKING;
        request_queue[request_queue_write] = req;
        if(request_queue_write == REQUEST_LASTIND) {
            request_queue_write = 0;
        }
        else {
            request_queue_write += 1;
        }
        printf("allocate: new write position %d\n", request_queue_write);
        return 1;
    }
}


static void *  
mfp_alloc_thread_func(void * data)
{
    mfp_alloc_reqinfo req; 

    printf("alloc_thread: started\n");

    while(mfp_alloc_quit == 0) {
        while(request_queue_read != request_queue_write) {
            printf("alloc_thread: found work to do at position %d\n",
                    request_queue_read);
            req = request_queue[request_queue_read];
            printf("alloc_thread: calling handler %p for proc %p\n", 
                    req.handler, req.proc);
            req.handler(req.proc, req.data);
            *req.status = ALLOC_READY; 
            printf("alloc_thread: all done with handler\n");
            request_queue_read = (request_queue_read+1) % REQUEST_BUFSIZE;
        }
        usleep(10000);
    }
    printf("alloc_thread: exiting\n");
    return NULL;
}


void
mfp_alloc_init(void)
{
    pthread_attr_t attr;

    pthread_attr_init(&attr);

    printf ("mfp_alloc_init() starting thread\n");
    pthread_create(&mfp_alloc_thread, NULL, &mfp_alloc_thread_func, NULL); 
    printf("mfp_alloc_init() pthread_create returned\n");
}

void
mfp_alloc_finish(void)
{
    mfp_alloc_quit = 1;
    pthread_join(mfp_alloc_thread, NULL);
}


