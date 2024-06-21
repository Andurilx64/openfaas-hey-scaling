"""Tests"""

from openfaas_watchtower import __version__


def test_version():
    """Assert the correct version"""
    assert __version__ == "0.1.0"
