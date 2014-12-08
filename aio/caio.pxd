cdef extern from "stdlib.h":
    int posix_memalign(void **memptr, size_t alignment, size_t size)

cdef extern from "string.h":
    void *memcpy(void *dest, void *src, size_t n)

cdef extern from "libaio.h":
    cdef struct io_context:
        pass
    ctypedef io_context *io_context_t

    cdef struct io_iocb_common:
        void *buf
        unsigned long nbytes
        unsigned resfd
        pass

    cdef struct io_iocb_vector:
        pass

    cdef struct io_iocb_poll:
        pass

    cdef struct io_iocb_sockaddr:
        pass

    cdef union U:
        io_iocb_common c
        io_iocb_vector v
        io_iocb_poll poll
        io_iocb_sockaddr saddr

    cdef struct iocb:
        void *data
        short aio_lio_opcode
        U u
        pass

    cdef struct io_event:
        unsigned data
        unsigned obj
        unsigned res
        unsigned res2
        pass

    cdef struct timespec:
        pass

    cdef enum io_iocb_cmd:
        IO_CMD_PREAD = 0
        IO_CMD_PWRITE = 1
        pass

    int io_setup(unsigned nr_events, io_context_t *ctxp)
    int io_submit(io_context_t ctx_id, long nr, iocb **iocbpp)
    int io_getevents(io_context_t ctx_id, long min_nr, long nr, io_event *events, timespec *timeout)
    void io_prep_pread(iocb *iocb, int fd, char *buf, size_t count, long long offset)
    void io_prep_pwrite(iocb *iocb, int fd, char *buf, size_t count, long long offset)
    int io_destroy(io_context_t ctx)
    void io_set_eventfd(iocb *iocb, int eventfd)
