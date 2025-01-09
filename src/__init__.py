import os
import sys

if getattr(sys, "frozen", False):
    inner_path = sys._MEIPASS
    application_path = os.path.dirname(sys.executable)
elif __file__:
    inner_path = os.getcwd()
    application_path = inner_path
