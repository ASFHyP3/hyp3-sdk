"""Errors and exceptions to raise when the SDK runs into problems"""


class HyP3Error(Exception):
    """Base Exception for Hyp3_sdk"""


class ValidationError(HyP3Error):
    """Raise when jobs do not pass validation"""


class AuthenticationError(HyP3Error):
    """Raise when authentication does not succeed"""
