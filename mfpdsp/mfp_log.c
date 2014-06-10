#include <stdarg.h>
#include <stdio.h>

#include "mfp_dsp.h" 
#define LOG_MAX 2048

void 
_mfp_log(const char * level, const char * site_filename, int site_lineno, ...)
{
    char logbuf[LOG_MAX];
    char * fmt;
    va_list args;
    va_start(args, site_lineno);
    fmt = va_arg(args, char *);
    vsnprintf(logbuf, LOG_MAX-1, fmt, args);
    va_end(args);
    printf("\n[LOG] %s: %s\n", level, logbuf);
    printf("\n[VERBOSE] %s: %s:%d %s\n", level, site_filename, site_lineno, logbuf);
    fflush(stdout);
}

