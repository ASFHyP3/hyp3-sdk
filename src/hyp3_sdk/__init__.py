"""A python wrapper around the HyP3 API"""

from importlib.metadata import version

from . import util
from .config import TESTING  # noqa
from .hyp3 import HyP3, PROD_API, TEST_API
from .jobs import Batch, Job


__version__ = version(__name__)

__all__ = [
    '__version__',
    'Batch',
    'HyP3',
    'Job',
    'PROD_API',
    'TEST_API',
    'util',
]
