from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules=[
    Extension("caio",
              ["aio.pyx"],
              libraries=["aio"])
]

setup(
  name = "Python Lib AIO bindings",
  cmdclass = {"build_ext": build_ext},
  ext_modules = ext_modules
)
