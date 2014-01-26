#include <glib.h>
#include <stdio.h>
#include <string.h>
#include <pthread.h>
#include <sys/stat.h>
#include <sys/socket.h> 
#include <sys/un.h>
#include <sys/unistd.h>

#include "mfp_dsp.h"

static char * comm_sockname = NULL;
static int comm_socket = -1;
static pthread_t comm_io_reader_thread;
static pthread_t comm_io_writer_thread;
static int comm_io_quitreq = 0;
static pmutex_t comm_io_lock = PTHREAD_MUTEX_INITIALIZER;

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
    address.sun_path = strndup(sockname, UNIX_PATH_MAX);

    if (connect(socket_fd, &address, sizeof(struct sockaddr_un)) < 0) {
        printf("mfp_comm_connect: connect() failed, is MFP running?\n");
        return -1;
    }

    comm_sockname = g_strdup(sockname);
    comm_socket = socket_fd; 
    return socket_fd;
}

int
mfp_comm_init(char * init_sockid) 
{
    char * env_sockid = getenv("MFP_SOCKET");
    int connectfd; 
    char * conn_sockid = NULL;

    printf("mfp_comm_init(): enter\n");

    if(init_socket > 0) {
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

    /* start the IO thread */ 
    mfp_comm_io_start();
    return 0;
}

void mfp_comm_io_start(void) {
    
    printf("mfp_comm_start_io(): enter\n");
    pthread_create(&comm_io_reader_thread, NULL, mfp_comm_io_reader_thread, NULL);
    pthread_create(&comm_io_writer_thread, NULL, mfp_comm_io_writer_thread, NULL);
}

void mfp_comm_io_finish(void) {
    pthread_mutex_lock(comm_io_mutex);
    comm_io_quitreq = 1;
    pthread_mutex_unlock(comm_io_mutex);

}

void mfp_comm_io_reader_thread(void * tdata) 
{
    int quitreq = 0;
    char msgbuf[MFP_MAX_MSGSIZE];
    int bytesread; 

    printf("mfp_comm_io_reader_thread: enter\n");
   
    while(!quitreq) {
        bytesread = recv(comm_socket, msgbuf, MFP_MAX_MSGSIZE, 0);     

        pthread_mutex_lock(comm_io_lock);
        quitreq = comm_io_quitreq;
        pthread_mutex_unlock(comm_io_lock);
    }


}

void mfp_comm_io_writer_thread(void * tdata) 
{
    int quitreq = 0;
    char msgbuf[MFP_MAX_MSGSIZE];
    int bytesread; 
    struct timespec alarmtime;
    struct timeval nowtime;

    printf("mfp_comm_io_writer_thread: enter\n");
   
    while(!quitreq) {
        bytesread = recv(comm_socket, msgbuf, MFP_MAX_MSGSIZE, 0);     

        pthread_mutex_lock(&mfp_response_lock);
        pthread_cond_wait(mfp_respose_cond);

        gettimeofday(&nowtime, NULL);
        alarmtime.tv_sec = nowtime.tv_sec; 
        alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;

        if (mfp_response_queue_read == mfp_response_queue_write) { 
            pthread_cond_timedwait(&mfp_response_cond, &mfp_response_lock, &alarmtime);
        }

        /* copy/clear C response objects */
        if(mfp_response_queue_read != mfp_response_queue_write) {
            l = PyList_New(0);
            while(mfp_response_queue_read != mfp_response_queue_write) {
                t = PyTuple_New(3);
                r = mfp_response_queue[mfp_response_queue_read];

                proc = g_hash_table_lookup(mfp_proc_objects, r.dst_proc);
                if (proc == NULL)
                    proc = Py_None;

                Py_INCREF(proc);

                PyTuple_SetItem(t, 0, proc);
                PyTuple_SetItem(t, 1, PyInt_FromLong(r.msg_type));
                switch(r.response_type) {
                    case PARAMTYPE_FLT:
                        PyTuple_SetItem(t, 2, PyFloat_FromDouble(r.response.f));
                        break;
                    case PARAMTYPE_BOOL:
                        PyTuple_SetItem(t, 2, PyBool_FromLong(r.response.i));
                        break;
                    case PARAMTYPE_INT:
                        PyTuple_SetItem(t, 2, PyInt_FromLong(r.response.i));
                        break;
                    case PARAMTYPE_STRING:
                        PyTuple_SetItem(t, 2, PyString_FromString(r.response.c));
                        g_free(r.response.c);
                        break;
                }
                PyList_Append(l, t);
                responses += 1;
                mfp_response_queue_read = (mfp_response_queue_read+1) % REQ_BUFSIZE;
            }
        }
        pthread_mutex_unlock(&mfp_response_lock);

        pthread_mutex_lock(comm_io_lock);
        quitreq = comm_io_quitreq;
        pthread_mutex_unlock(comm_io_lock);
    }


}

void mfp_comm_io_run(void)
{
    void * thread_result;

    mfp_comm_io_start();
    pthread_join(comm_io_thread, *result);
}

