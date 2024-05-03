from importlib import import_module


missing_modules = []
needed_modules = ['aiohttp', 'fsspec', 'h5py', 'pyproj', 'pystac', 'odc.stac', 'tifffile']
for module in needed_modules:
    try:
        import_module(module)
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    raise ImportError(f'package(s) {", ".join(missing_modules)} is/are required for this submodule.')
