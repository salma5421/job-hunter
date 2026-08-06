import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from server import SystemAPIHandler

app = SystemAPIHandler
handler = SystemAPIHandler
