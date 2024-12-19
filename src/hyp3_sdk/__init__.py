"""A python wrapper around the HyP3 API"""

from importlib.metadata import version

from . import util
from .hyp3 import PROD_API, TEST_API, HyP3
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
