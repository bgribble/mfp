#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <errno.h>
#include <sys/stat.h>
#include <sys/socket.h> 
#include <sys/time.h>
#include <linux/un.h> 
#include <sys/unistd.h>
#include <json-glib/json-glib.h>
#include "mfp_dsp.h"

int mfp_comm_nodeid = -1;
static char * comm_sockname = NULL;
static int comm_socket = -1;
static int comm_procpid = -1;
static pthread_t comm_io_reader_thread;
static pthread_t comm_io_writer_thread;
static int comm_io_quitreq = 0;
static pthread_mutex_t comm_io_lock = PTHREAD_MUTEX_INITIALIZER;

typedef struct {
    char bufdata[MFP_MAX_MSGSIZE];
    int free;
} comm_bufblock;

static comm_bufblock comm_buffers[MFP_NUM_BUFFERS];

int
mfp_comm_connect(char * sockname) 
{
    int socket_fd;
    struct sockaddr_un address; 
    struct timeval tv; 

    tv.tv_sec = 0;
    tv.tv_usec = 100000;

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

    setsockopt(socket_fd, SOL_SOCKET, SO_RCVTIMEO,(char *)&tv,sizeof(struct timeval));

    comm_sockname = g_strdup(sockname);
    comm_socket = socket_fd; 
    return socket_fd;
}


char * 
mfp_comm_get_buffer(void)
{
    /* FIXME mfp_comm_get_buffer implementation is naive */ 
    for(int bufnum=0; bufnum < MFP_NUM_BUFFERS; bufnum++) {
        if(comm_buffers[bufnum].free) {
            comm_buffers[bufnum].free = 0;
            return comm_buffers[bufnum].bufdata;
        }
    }

    printf("mfp_comm_get_buffer: no buffers free!\n");
    return NULL;
}

void
mfp_comm_release_buffer(char * msgbuf)
{
    /* FIXME mfp_comm_get_buffer implementation is naive */ 
    for(int bufnum=0; bufnum < MFP_NUM_BUFFERS; bufnum++) {
        if(comm_buffers[bufnum].bufdata == msgbuf) {
            comm_buffers[bufnum].free = 1;
            return;
        }
    }

    printf("mfp_comm_release_buffer: no matching buffer found!\n");
    return;
}

int 
mfp_comm_submit_buffer(char * msgbuf, int msglen) 
{
    mfp_out_data rd;
    rd.msgbuf = msgbuf;
    rd.msglen = msglen;

    if (msgbuf == NULL) {
        printf("mfp_comm_submit_buffer: no buffer, skipping\n");
        return 0;
    }

    if((outgoing_queue_read == 0 && outgoing_queue_write == REQ_LASTIND)
        || (outgoing_queue_write + 1 == outgoing_queue_read)) {
        return 0;
    }

    outgoing_queue[outgoing_queue_write] = rd;
    if(outgoing_queue_write == REQ_LASTIND) {
        outgoing_queue_write = 0;
    }
    else {
        outgoing_queue_write += 1;
    }

    pthread_cond_broadcast(&outgoing_cond);
    return 1;
}

int 
mfp_comm_send_buffer(char * msg, int msglen)
{
    char pbuff[11];
    snprintf(pbuff, 10, "% 8d", msglen); 
    pthread_mutex_lock(&comm_io_lock);
    send(comm_socket, "[ SYNC ]", 8, 0);
    send(comm_socket, pbuff, 8, 0);
    send(comm_socket, msg, msglen, 0);
    pthread_mutex_unlock(&comm_io_lock);
    mfp_comm_release_buffer(msg);
}

static int
mfp_comm_launch(char * sockname)
{
    char mfpcmd[MFP_EXEC_SHELLMAX];  
    char * const execargs[4] = {"/bin/bash", "-c", mfpcmd, NULL};

    snprintf(mfpcmd, MFP_EXEC_SHELLMAX-1, "mfp --no-dsp --no-default -s %s", sockname);

    printf("mfp_comm_launch: Launching main mfp process with '%s'\n", mfpcmd);

    if (comm_procpid = fork()) {
        printf("mfp_comm_launch (parent): got child PID %d\n", comm_procpid);
        printf("mfp_comm_launch (parent): waiting for child startup\n");
        /* FIXME need to get some positive confirmation that MFP is up */
        sleep(2);
        return 0;
    }
    else {
        printf("mfp_comm_launch (child): about to exec\n");
        execv("/bin/bash", execargs);
        printf("mfp_comm_launch: exec failed\n");
        perror("execve");
    }

}

int 
mfp_comm_quit_requested(void) 
{
    int quitreq; 
    pthread_mutex_lock(&comm_io_lock);
    quitreq = comm_io_quitreq;
    pthread_mutex_unlock(&comm_io_lock);

    return quitreq;
}

int
mfp_comm_init(char * init_sockid) 
{
    char * env_sockid = getenv("MFP_SOCKET");
    int connectfd; 
    char * conn_sockid = NULL;
    int connect_tries = 0;

    for(int bufno=0; bufno < MFP_NUM_BUFFERS; bufno++) {
        comm_buffers[bufno].free = 1;
        bzero(comm_buffers[bufno].bufdata, MFP_MAX_MSGSIZE);
    }


    if(init_sockid > 0) {
        conn_sockid = init_sockid;
    }
    else if (env_sockid != NULL) { 
        conn_sockid = env_sockid;
    }
    else {
        conn_sockid = MFP_DEFAULT_SOCKET;
    }

    connectfd = mfp_comm_connect(conn_sockid);

    if (connectfd < 0) {
        printf("mfp_comm_init: can't connect to MFP, trying to start\n");
        mfp_comm_launch(conn_sockid);

        while(connect_tries < 10) {
            /* try again */
            connectfd = mfp_comm_connect(conn_sockid);

            if (connectfd < 0) {
                printf("mfp_comm_init: connect attempt %d failed\n", connect_tries);
                sleep(1);
                connect_tries ++;
            }
            else {
                break;
            }
        }
        if (connect_tries == 10) {
            printf("mfp_comm_init: can't connect after 10 tries, giving up\n");
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
    int  phase=0;
    int  mlen = 0;
    char syncbuf[]={0,0,0,0,0,0,0,0,0,0};
    char lenbuf[]={0,0,0,0,0,0,0,0,0,0};
    char msgbuf[MFP_MAX_MSGSIZE+1];
    int bytesread; 
    int success = 0;
    int errstat = 0; 

    while(!quitreq) {
        bzero(msgbuf, MFP_MAX_MSGSIZE+1);
        if (phase == 0) {
            bytesread = recv(comm_socket, syncbuf, 8, 0);  
            if (bytesread == 8) { 
                errstat = 0;
                success = 1;
                phase = 1;
            }
            else 
                success = 0;
        }
        else if (phase == 1) {
            bytesread = recv(comm_socket, lenbuf, 8, 0);  
            if (bytesread == 8) { 
                errstat = 0;
                mlen = atoi(lenbuf);
                success = 1;
                phase = 2;
            }
            else 
                success = 0;
        }
        else if (phase == 2) {
            bytesread = recv(comm_socket, msgbuf, mlen, 0);  
            if (bytesread == mlen) { 
                errstat = 0;
                mlen = atoi(lenbuf);
                phase = 0;
                success = 1;
                // printf("    [0 --> %d]\n%s\n", mfp_comm_nodeid, msgbuf);
                mfp_rpc_dispatch_request(msgbuf, bytesread);
            }
            else 
                success = 0;
        }

        if (!success) {
            if (errno != EWOULDBLOCK && errno != EAGAIN) {
                if (errstat == 0) {
                    printf("comm IO reader: error reading from socket %d\n", comm_socket);
                    errstat = 1;
                }
            }
        }
        quitreq = mfp_comm_quit_requested();
    }
}

static void * 
mfp_comm_io_writer_thread(void * tdata) 
{
    int quitreq = 0;
    char msgbuf[MFP_MAX_MSGSIZE];
    GArray * rdata;
    struct timespec alarmtime;
    struct timeval nowtime;
    mfp_out_data r;
    char pbuff[32];

    rdata = g_array_new(TRUE, TRUE, sizeof(mfp_out_data));

    while(!quitreq) {
        /* wait for a signal that there's data to write */ 
        pthread_mutex_lock(&outgoing_lock);
        pthread_cond_wait(&outgoing_cond, &outgoing_lock);

        gettimeofday(&nowtime, NULL);
        alarmtime.tv_sec = nowtime.tv_sec; 
        alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;

        if (outgoing_queue_read == outgoing_queue_write) { 
            pthread_cond_timedwait(&outgoing_cond, &outgoing_lock, &alarmtime);
        }

        /* copy/clear C response objects */
        if(outgoing_queue_read != outgoing_queue_write) {
            while(outgoing_queue_read != outgoing_queue_write) {
                r = outgoing_queue[outgoing_queue_read];
                g_array_append_val(rdata, r);
                outgoing_queue_read = (outgoing_queue_read+1) % REQ_BUFSIZE;
            }
        }
        pthread_mutex_unlock(&outgoing_lock);

        for(int reqno=0; reqno < rdata->len; reqno++) {
            r = g_array_index(rdata, mfp_out_data, reqno);
            mfp_comm_send_buffer(r.msgbuf, r.msglen);
        }
        if (rdata->len > 0) { 
            g_array_remove_range(rdata, 0, rdata->len);
        }

        pthread_mutex_lock(&comm_io_lock);
        quitreq = comm_io_quitreq;
        pthread_mutex_unlock(&comm_io_lock);
    }


}

void 
mfp_comm_io_start(void) 
{
    pthread_create(&comm_io_reader_thread, NULL, mfp_comm_io_reader_thread, NULL);
    pthread_create(&comm_io_writer_thread, NULL, mfp_comm_io_writer_thread, NULL);
}

void 
mfp_comm_io_wait(void) 
{
    pthread_join(comm_io_reader_thread, NULL);
    pthread_join(comm_io_writer_thread, NULL);
}

void 
mfp_comm_io_finish(void) 
{
    pthread_mutex_lock(&comm_io_lock);
    comm_io_quitreq = 1;
    pthread_cond_broadcast(&outgoing_cond);
    pthread_mutex_unlock(&comm_io_lock);
    mfp_comm_io_wait();
}

