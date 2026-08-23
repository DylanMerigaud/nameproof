"""Entry point for `python3 -m nameproof`.

The plugin wrapper in bin/ calls the package this way rather than through the console script,
because a plugin is copied to a cache directory and never pip-installed: there is no console
script to call, only a package sitting on PYTHONPATH.
"""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
