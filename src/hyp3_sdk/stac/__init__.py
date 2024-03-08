missing_modules = []
try:
    import fsspec  # noqa F401
except ImportError:
    missing_modules.append('fsspec')

try:
    import h5py  # noqa F401
except ImportError:
    missing_modules.append('h5py')

try:
    import pyproj  # noqa F401
except ImportError:
    missing_modules.append('pyproj')

try:
    import pystac  # noqa F401
except ImportError:
    missing_modules.append('pystac')

try:
    import odc.stac  # noqa F401
except ImportError:
    missing_modules.append('odc-stac')

try:
    import tifffile  # noqa F401
except ImportError:
    missing_modules.append('tifffile')

if missing_modules:
    raise ImportError(f'package(s) {" ,".join(missing_modules)} is/are required for this submodule.')
