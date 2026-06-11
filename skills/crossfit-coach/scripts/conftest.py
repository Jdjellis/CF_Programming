"""Put the vendored `cfprog` package on the path for the test run.

The scripts are invoked as `python3 scripts/<name>.py` and add this directory to
sys.path themselves; this conftest does the same for pytest so the tests under
`scripts/tests/` can `import cfprog` without an install step.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
