"""A python wrapper around the HyP3 API"""

# FIXME: Python 3.8+ this should be `from importlib.metadata...`
from importlib_metadata import PackageNotFoundError, version

from .hyp3 import HYP3_PROD, HYP3_TEST, HyP3
from .jobs import Job, make_autorift_job, make_insar_gamma_job, make_rtc_gamma_job

try:
    __version__ = version(__name__)
except PackageNotFoundError:
    print('package is not installed!\n'
          'Install in editable/develop mode via (from the top of this repo):\n'
          '   python -m pip install -e .\n'
          'Or, to just get the version number use:\n'
          '   python setup.py --version')

__all__ = [
    'HyP3',
    'HYP3_PROD',
    'HYP3_TEST',
    'Job',
    'make_autorift_job',
    'make_insar_gamma_job',
    'make_rtc_gamma_job',
    '__version__',
]
