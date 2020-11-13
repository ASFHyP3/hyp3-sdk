"""Errors and exceptions to raise when the SDK runs into problems"""

class Hyp3SdkError(Exception):
    """Base Exception for Hyp3_sdk"""


class ValidationError(Hyp3SdkError):
    """Raise when jobs do not pass validation"""


class AuthenticationError(Hyp3SdkError):
    """Raise when authentication does not succeed"""
