import cython
cimport caio

from cpython.mem cimport PyMem_Malloc, PyMem_Free
from cpython.string cimport PyString_FromStringAndSize, PyString_AS_STRING, PyString_InternFromString
from cpython.ref cimport PyObject
from libc.stdio cimport printf

cdef class AIO:
    cdef caio.io_context_t ctx
    cdef caio.iocb **iocbs
    cdef caio.iocb *iocba
    cdef caio.io_event *events
    cdef int curiocb
    cdef int maxiocbs

    def __cinit__(self):
        self.ctx = <io_context_t> 0

    cpdef int io_setup(self, unsigned nr_events=4096) except -1:
        cdef caio.iocb *_dummy = <iocb *> 0

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

    def io_read(self, int fd, size_t count, long long offset, long long cookie = 0):
        cdef caio.iocb *iocb = <caio.iocb *> &self.iocba[self.curiocb]
        buf = PyString_FromStringAndSize(NULL, count)
        if not buf:
            raise MemoryError()
        self.io_prep_pread(iocb, fd, PyString_AS_STRING(buf), count, offset)
        iocb.data = <void *>cookie
        self.io_addiocb(iocb)
        return buf

    def io_write(self, int fd, char *buf, size_t count, long long offset, long long cookie = 0):
        cdef caio.iocb *iocb = <caio.iocb *> &self.iocba[self.curiocb]
        self.io_prep_pwrite(iocb, fd, buf, count, offset)
        iocb.data = <void *>cookie
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

        ret = caio.io_getevents(self.ctx, 0, self.curiocb, self.events, NULL)
        complete = {'reads':[], 'writes':[], 'total':0}
        while i < ret:
            iocb = <caio.iocb *>(self.events[i].obj)
            event = <caio.io_event *>(&self.events[i])
            if iocb.aio_lio_opcode == IO_CMD_PREAD:
                complete['reads'].append((<unsigned long long>iocb.data, event.res, PyString_InternFromString(<char *>iocb.u.c.buf)))
            elif iocb.aio_lio_opcode == IO_CMD_PWRITE:
                complete['writes'].append((<unsigned long long>iocb.data, event.res))
            i += 1

        complete['total'] = ret
        return complete

    def __dealloc__(self):
        caio.io_destroy(self.ctx)
        if self.events:
            PyMem_Free(self.events)

        if self.iocbs:
            PyMem_Free(self.iocbs)
