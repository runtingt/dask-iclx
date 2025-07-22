import logging as _logging
from .cluster import ICCluster
from .config import _ensure_user_config_file, _set_base_config

_logger = _logging.getLogger(__name__)
_logger.setLevel(_logging.DEBUG)
_logger.addHandler(_logging.NullHandler())

_ensure_user_config_file()
_set_base_config()

__all__ = ["ICCluster"]
