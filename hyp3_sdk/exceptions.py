"""Errors and exceptions to raise when the SDK runs into problems"""


class HyP3Error(Exception):
    """Base Exception for the HyP3 SDK"""


class ASFSearchError(HyP3Error):
    """Raise for errors when using the ASF Search module"""


class AuthenticationError(HyP3Error):
    """Raise when authentication does not succeed"""
