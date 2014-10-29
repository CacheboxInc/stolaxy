from libc.stdlib cimport atoi

def say_hello_to(name):
    print("Hello %s!" % name)

cpdef parse_charptr_to_py_int(char* s):
    assert s is not NULL, "byte string value is NULL"
    return atoi(s)   # note: atoi() has no error detection!

cdef extern from "string.h":
    char* strstr(const char *haystack, const char *needle)

cpdef char *strstr2(const char *haystack, const char *needle):
      return strstr(haystack, needle)