"""SageMaker entry point (Python, so the training toolkit runs it the standard way); delegates to sm_entry.sh."""
import os
import subprocess
import sys

here = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.call(["bash", os.path.join(here, "sm_entry.sh")]))
