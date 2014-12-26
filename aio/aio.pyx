import cython
cimport caio

from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.string cimport PyString_FromStringAndSize, PyString_AS_STRING, PyString_InternFromString, PyString_FromString
from cpython.ref cimport PyObject
from libc.stdio cimport printf
from libc.stdlib cimport malloc, free

cdef class AIO:
    cdef caio.io_context_t ctx
    cdef caio.iocb **iocbs
    cdef caio.iocb *iocba
    cdef caio.io_event *events
    cdef int curiocb
    cdef int maxiocbs
    cdef size_t size
    cdef dict addresses

    def __cinit__(self):
        self.ctx = <io_context_t> 0

    cpdef int io_setup(self, unsigned nr_events=4096) except -1:
        cdef caio.iocb *_dummy = <iocb *> 0

        self.size = 0
        self.addresses = {}

        if caio.io_setup(nr_events, &self.ctx) != 0:
            raise MemoryError()

        self.iocbs = <caio.iocb **>PyMem_Malloc(nr_events * cython.sizeof(_dummy))
        if not self.iocbs:
            raise MemoryError()

        self.events = <caio.io_event *>PyMem_Malloc(nr_events * cython.sizeof(caio.io_event))
        if not self.events:
            raise MemoryError()

        self.iocba = <caio.iocb *>PyMem_Malloc(nr_events * cython.sizeof(caio.iocb))

        self.curiocb = 0
        self.maxiocbs = nr_events

    cdef io_prep_pread(self, caio.iocb *iocb, int fd, char *buf, size_t count, long long offset):
        caio.io_prep_pread(iocb, fd, buf, count, offset)

    cdef void io_prep_pwrite(self, caio.iocb *iocb, int fd, char *buf, size_t count, long long offset):
        caio.io_prep_pwrite(iocb, fd, buf, count, offset)

    cdef int io_addiocb(self, caio.iocb *iocb) except -1:
        if self.curiocb == self.maxiocbs:
            raise MemoryError() # TBD: fixthis

        self.iocbs[self.curiocb] = iocb
        self.curiocb += 1

    def io_read(self, int fd, size_t count, long long offset, long long xid):
        cdef caio.iocb *iocb = <caio.iocb *> &self.iocba[self.curiocb]
        cdef char *buf = <char *> PyMem_Malloc(count)
        cdef size_t addr = <size_t> buf
        cdef caio.aio_cookie_t cookie = <caio.aio_cookie_t>PyMem_Malloc(caio.aio_cookie_size)
        self.addresses[addr] = count
        if buf == NULL:
            raise MemoryError()
        if (count % 512) == 0 and (offset % 512) == 0:
            r = posix_memalign(<void **>&buf, 512, count)
            if r != 0:
                raise MemoryError()
        self.io_prep_pread(iocb, fd, buf, count, offset)
        cookie.xid = xid
        cookie.addr = addr
        iocb.data = <void *> cookie
        self.size += count
        self.io_addiocb(iocb)
        return buf

    def io_write(self, int fd, char *buf, size_t count, long long offset, long long xid):
        cdef caio.iocb *iocb = <caio.iocb *> &self.iocba[self.curiocb]
        cdef char *c_buf = <char *> PyMem_Malloc(count)
        cdef size_t addr = <size_t> c_buf
        cdef caio.aio_cookie_t cookie = <caio.aio_cookie_t>PyMem_Malloc(caio.aio_cookie_size)
        self.addresses[addr] = count
        if (count % 512) == 0 and (offset % 512) == 0:
            r = posix_memalign(<void **>&c_buf, 512, count)
            if r != 0:
                raise MemoryError()
        c_buf = <char *>memcpy(<void *>c_buf, <void *>buf, count)
        self.io_prep_pwrite(iocb, fd, c_buf, count, offset)
        cookie.xid = xid
        cookie.addr = addr
        iocb.data = <void *> cookie
        self.size += count
        return self.io_addiocb(iocb)

    def io_submit(self):
        return caio.io_submit(self.ctx, self.curiocb, self.iocbs)

    def io_reset(self):
        self.curiocb = 0

    def io_getevents(self):
        cdef int ret
        cdef int i = 0
        cdef caio.iocb *iocb
        cdef caio.io_event *event
        cdef long long xid
        cdef size_t addr
        cdef size_t io_addr
        cdef size_t count
        cdef caio.aio_cookie_t cookie

        ret = caio.io_getevents(self.ctx, 0, self.curiocb, self.events, NULL)
        complete = {'reads':[], 'writes':[], 'total':0}
        while i < ret:
            iocb = <caio.iocb *>(self.events[i].obj)
            event = <caio.io_event *>(&self.events[i])
            cookie = <caio.aio_cookie_t> iocb.data
            xid = cookie.xid
            addr = cookie.addr
            if iocb.aio_lio_opcode == IO_CMD_PREAD:
                complete['reads'].append((xid, event.res, PyString_FromStringAndSize(<char *>iocb.u.c.buf, event.res)))
                io_addr = <size_t> iocb.u.c.buf
                PyMem_Free(<void *>io_addr)
            elif iocb.aio_lio_opcode == IO_CMD_PWRITE:
                complete['writes'].append((xid, event.res))
                io_addr = <size_t> iocb.u.c.buf
                PyMem_Free(<void *>io_addr)
            count = self.addresses.pop(addr)
            if io_addr != addr:
                PyMem_Free(<void *> addr)
            PyMem_Free(<void *> cookie)
            self.size -= count
            i += 1

        complete['total'] = ret
        return complete

    def __dealloc__(self):
        caio.io_destroy(self.ctx)
        if self.events:
            PyMem_Free(self.events)

        if self.iocbs:
            PyMem_Free(self.iocbs)
