try:
    from ._version import version as __version__
except ImportError:
    # broken installation, we don't even try (copied from pytest implementation)
    __version__ = "unknown"
