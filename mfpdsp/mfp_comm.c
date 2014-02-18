#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <sys/stat.h>
#include <sys/socket.h> 
#include <sys/time.h>
#include <linux/un.h> 
#include <sys/unistd.h>
#include <json-glib/json-glib.h>
#include "mfp_dsp.h"

#define MFP_PORT_DEFAULT "/tmp/mfp_socket"
#define MFP_MAX_MSGSIZE 2048 

static char * comm_sockname = NULL;
static int comm_socket = -1;
static pthread_t comm_io_reader_thread;
static pthread_t comm_io_writer_thread;
static int comm_io_quitreq = 0;
static pthread_mutex_t comm_io_lock = PTHREAD_MUTEX_INITIALIZER;

int
mfp_comm_connect(char * sockname) 
{
    int socket_fd;
    struct sockaddr_un address; 

    printf("mfp_comm_connect: enter\n");

    socket_fd = socket(PF_UNIX, SOCK_STREAM, 0);
    if (socket_fd < 0) {
        printf("mfp_comm_connect: socket() failed\n");
        return -1;
    }

    memset(&address, 0, sizeof(struct sockaddr_un));
    address.sun_family = AF_UNIX;
    strncpy(address.sun_path, sockname, UNIX_PATH_MAX);

    if (connect(socket_fd, (struct sockaddr *)&address, sizeof(struct sockaddr_un)) < 0) {
        printf("mfp_comm_connect: connect() failed, is MFP running?\n");
        return -1;
    }

    comm_sockname = g_strdup(sockname);
    comm_socket = socket_fd; 
    return socket_fd;
}

static int
mfp_comm_launch(char * sockid)
{
    printf("Launching main mfp process\n");
}


int
mfp_comm_init(char * init_sockid) 
{
    char * env_sockid = getenv("MFP_SOCKET");
    int connectfd; 
    char * conn_sockid = NULL;

    printf("mfp_comm_init(): enter\n");

    if(init_sockid > 0) {
        conn_sockid = init_sockid;
    }
    else if (env_sockid != NULL) { 
        conn_sockid = env_sockid;
    }
    else {
        conn_sockid = MFP_PORT_DEFAULT;
    }

    connectfd = mfp_comm_connect(conn_sockid);

    if (connectfd < 0) {
        printf("mfp_comm_init: can't connect to MFP, trying to start\n");
        mfp_comm_launch(conn_sockid);

        /* try again */
        connectfd = mfp_comm_connect(conn_sockid);

        if (connectfd < 0) {
            printf("mfp_comm_init: can't connect to MFP on second try, giving up\n");
            return -1;
        }
    }

    /* start the IO threads */ 
    mfp_comm_io_start();
    return 0;
}

static void *  
mfp_comm_io_reader_thread(void * tdata) 
{
    int quitreq = 0;
    char msgbuf[MFP_MAX_MSGSIZE];
    int bytesread; 

    printf("mfp_comm_io_reader_thread: enter\n");
   
    while(!quitreq) {
        bytesread = recv(comm_socket, msgbuf, MFP_MAX_MSGSIZE, 0);     

        mfp_rpc_dispatch(msgbuf, bytesread);

        pthread_mutex_lock(&comm_io_lock);
        quitreq = comm_io_quitreq;
        pthread_mutex_unlock(&comm_io_lock);
    }
}

static void * 
mfp_comm_io_writer_thread(void * tdata) 
{
    int quitreq = 0;
    char  * msgbuf;
    GArray * rdata;
    struct timespec alarmtime;
    struct timeval nowtime;
    mfp_respdata r;
    char pbuff[32];

    printf("mfp_comm_io_writer_thread: enter\n");
    jdata = g_array_new(TRUE, TRUE, sizeof(mfp_respdata));

    while(!quitreq) {
        /* wait for a signal that there's data to write */ 
        pthread_mutex_lock(&mfp_response_lock);
        pthread_cond_wait(&mfp_response_cond, &mfp_response_lock);

        gettimeofday(&nowtime, NULL);
        alarmtime.tv_sec = nowtime.tv_sec; 
        alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;

        if (mfp_response_queue_read == mfp_response_queue_write) { 
            pthread_cond_timedwait(&mfp_response_cond, &mfp_response_lock, &alarmtime);
        }

        /* copy/clear C response objects */
        if(mfp_response_queue_read != mfp_response_queue_write) {
            while(mfp_response_queue_read != mfp_response_queue_write) {
                r = mfp_response_queue[mfp_response_queue_read];
                g_array_append(jdata, r);
                mfp_response_queue_read = (mfp_response_queue_read+1) % REQ_BUFSIZE;
            }
        }
        pthread_mutex_unlock(&mfp_response_lock);

        /* convert built list to text */ 
        for(int reqno=0; reqno < rdata->len; reqno++) {
            mfp_rpc_json_build(g_array_index(rdata, mfp_respdata, reqno), 
                               msgbuf); 
            send(comm_socket, msgbuf, strlen(msgbuf), 0);     

        }
        g_array_remove_range(rdata, 0, rdata->len);
        pthread_mutex_lock(&comm_io_lock);
        quitreq = comm_io_quitreq;
        pthread_mutex_unlock(&comm_io_lock);
    }


}

void 
mfp_comm_io_start(void) 
{
    printf("mfp_comm_start_io(): enter\n");
    pthread_create(&comm_io_reader_thread, NULL, mfp_comm_io_reader_thread, NULL);
    pthread_create(&comm_io_writer_thread, NULL, mfp_comm_io_writer_thread, NULL);
}

void 
mfp_comm_io_wait(void) 
{
    printf("mfp_comm_io_wait(): enter\n");
    pthread_join(comm_io_reader_thread, NULL);
    pthread_join(comm_io_writer_thread, NULL);
}

void 
mfp_comm_io_finish(void) 
{
    pthread_mutex_lock(&comm_io_lock);
    comm_io_quitreq = 1;
    pthread_mutex_unlock(&comm_io_lock);
    mfp_comm_io_wait();
}

