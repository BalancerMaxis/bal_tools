"""Test version import"""

import re
from bal_tools import __version__


def test_version():
    """Test version can be imported and follows semantic versioning"""
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0

    # check semantic version format: x.y.z with optional pre-release/build metadata
    # eg: 1.0.0, 1.0.0-beta, 1.0.0-alpha.1, 1.0.0+20130313144700
    version_pattern = r"^\d+\.\d+\.\d+([-.+].*)?$"
    assert re.match(version_pattern, __version__)
