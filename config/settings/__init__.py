import os
from .base import *

# Load settings based on deployment environment
if os.environ.get('AWS_EXECUTION_ENV') or os.environ.get('AWS'):
    from .aws import *
elif os.environ.get('RENDER'):
    from .production import *
else:
    from .local import *
