/* Generated by the protocol buffer compiler.  DO NOT EDIT! */
/* Generated from: envelope.proto */

#ifndef PROTOBUF_C_envelope_2eproto__INCLUDED
#define PROTOBUF_C_envelope_2eproto__INCLUDED

#include <protobuf-c/protobuf-c.h>

PROTOBUF_C__BEGIN_DECLS

#if PROTOBUF_C_VERSION_NUMBER < 1003000
# error This file was generated by a newer version of protoc-c which is incompatible with your libprotobuf-c headers. Please update your headers.
#elif 1004001 < PROTOBUF_C_MIN_COMPILER_VERSION
# error This file was generated by an older version of protoc-c which is incompatible with your libprotobuf-c headers. Please regenerate this file with a newer version of protoc-c.
#endif


typedef struct Carp__Envelope Carp__Envelope;


/* --- enums --- */


/* --- messages --- */

struct  Carp__Envelope
{
  ProtobufCMessage base;
  char *content_type;
  ProtobufCBinaryData content;
};
#define CARP__ENVELOPE__INIT \
 { PROTOBUF_C_MESSAGE_INIT (&carp__envelope__descriptor) \
    , (char *)protobuf_c_empty_string, {0,NULL} }


/* Carp__Envelope methods */
void   carp__envelope__init
                     (Carp__Envelope         *message);
size_t carp__envelope__get_packed_size
                     (const Carp__Envelope   *message);
size_t carp__envelope__pack
                     (const Carp__Envelope   *message,
                      uint8_t             *out);
size_t carp__envelope__pack_to_buffer
                     (const Carp__Envelope   *message,
                      ProtobufCBuffer     *buffer);
Carp__Envelope *
       carp__envelope__unpack
                     (ProtobufCAllocator  *allocator,
                      size_t               len,
                      const uint8_t       *data);
void   carp__envelope__free_unpacked
                     (Carp__Envelope *message,
                      ProtobufCAllocator *allocator);
/* --- per-message closures --- */

typedef void (*Carp__Envelope_Closure)
                 (const Carp__Envelope *message,
                  void *closure_data);

/* --- services --- */


/* --- descriptors --- */

extern const ProtobufCMessageDescriptor carp__envelope__descriptor;

PROTOBUF_C__END_DECLS


#endif  /* PROTOBUF_C_envelope_2eproto__INCLUDED */
