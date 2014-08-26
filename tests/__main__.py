
import os
import sys
import unittest

try:
    import dev_appserver
except ImportError, e:
    raise ImportError, "App Engine must be in PYTHONPATH."
    sys.exit()

os.environ["SERVER_SOFTWARE"] = "DevelopmentTesting"

test_path = sys.argv[0]

dev_appserver.fix_sys_path()

# fix_sys_path removes the current working directory, so we add it back in
sys.path.append('.')

# needed to be able to import the third party libraries
from config import BLOG_PATH
sys.path.append(os.path.dirname(BLOG_PATH))
sys.path.append(os.path.join(BLOG_PATH, 'lib', 'webtest'))

suite = unittest.loader.TestLoader().discover(test_path)
unittest.TextTestRunner(verbosity=2).run(suite)
