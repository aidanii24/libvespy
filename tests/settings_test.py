import os

class paths:
    BASE_DIR = os.path.dirname(__file__)
    CONTROL_DIR = os.path.join(BASE_DIR, 'control')
    ARTIFACTS_DIR = os.path.join(BASE_DIR, 'artifacts')