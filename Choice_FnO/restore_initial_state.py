import os
import shutil

def restore_initial_state():
    src = "state_snapshot.initial.json"
    dst = "state_snapshot.json"
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print("Successfully restored state_snapshot.json from state_snapshot.initial.json!")
    else:
        print(f"Initial state file {src} not found.")

if __name__ == "__main__":
    restore_initial_state()
