import os
from .base import *

# Load production or local settings based on environment
if os.environ.get('RENDER'):
    from .production import *
else:
    from .local import *
