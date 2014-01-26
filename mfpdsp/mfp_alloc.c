#include <stdio.h>
#include <unistd.h>
#include <pthread.h>

#include "mfp_dsp.h"
#include <time.h>

typedef struct {
    mfp_processor * proc;
    void (* handler)(mfp_processor *, void *); 
    void * data;
    int * status;
} mfp_alloc_reqinfo;

#define ALLOC_BUFSIZE 128
#define ALLOC_LASTIND 127 

mfp_alloc_reqinfo alloc_queue[ALLOC_BUFSIZE];
int alloc_queue_read = 0;
int alloc_queue_write = 0;

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
    
    if((alloc_queue_read == 0 && alloc_queue_write == ALLOC_LASTIND)
        || (alloc_queue_write + 1 == alloc_queue_read)) {
        *req_status = ALLOC_IDLE;
        return 0;
    }
    else {
        *req_status = ALLOC_WORKING;
        alloc_queue[alloc_queue_write] = req;
        if(alloc_queue_write == ALLOC_LASTIND) {
            alloc_queue_write = 0;
        }
        else {
            alloc_queue_write += 1;
        }
        return 1;
    }
}


static void *  
mfp_alloc_thread_func(void * data)
{
    mfp_alloc_reqinfo req; 
    struct timespec sleeptime;
    sleeptime.tv_sec = 0; sleeptime.tv_nsec = 100000;

    while(mfp_alloc_quit == 0) {
        while(alloc_queue_read != alloc_queue_write) {
            req = alloc_queue[alloc_queue_read];
            req.handler(req.proc, req.data);
            *req.status = ALLOC_READY; 
            alloc_queue_read = (alloc_queue_read+1) % ALLOC_BUFSIZE;
        }
        nanosleep(&sleeptime, NULL);
    }
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


