"""Shared product-center configuration.

This module is the stable import path for cross-platform code. The current
Android implementation still owns the concrete configuration in the legacy
root module, so this file re-exports it while the project is migrated.
"""

from product_center_config import *  # noqa: F401,F403

