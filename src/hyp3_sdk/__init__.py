"""A python wrapper around the HyP3 API"""

from importlib.metadata import PackageNotFoundError, version

from .config import TESTING  # noqa
from .hyp3 import HyP3, PROD_API, TEST_API
from .jobs import Batch, Job

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    print('package is not installed!\n'
          'Install in editable/develop mode via (from the top of this repo):\n'
          '   python -m pip install -e .\n'
          'Or, to just get the version number use:\n'
          '   python setup.py --version')

__all__ = [
    'Batch',
    'HyP3',
    'PROD_API',
    'TEST_API',
    'Job',
    '__version__',
]
