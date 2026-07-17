import os
import sys
import streamlit.web.cli as stcli

def resolve_path(path):
    if getattr(sys, 'frozen', False):
        # We are running as a PyInstaller bundle
        base_path = sys._MEIPASS
    else:
        # We are running from a normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, path)

if __name__ == "__main__":
    script_path = resolve_path("dashboard.py")
    sys.argv = ["streamlit", "run", script_path, "--global.developmentMode=false"]
    sys.exit(stcli.main())
