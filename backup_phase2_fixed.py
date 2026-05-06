import os
import shutil
from datetime import datetime

def main():
    src = r"E:\Axiom"
    dst = r"E:\_AXIOM_BACKUPS\Axiom_v0.2.0_phase2_data_chain_20260503"
    # Ensure parent exists
    parent = os.path.dirname(dst)
    if not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)
    # If destination exists, fail gracefully
    if os.path.exists(dst):
        print(f"Backup target already exists: {dst}")
        return
    shutil.copytree(src, dst)
    print(f"Backup created: {dst}")

if __name__ == '__main__':
    main()
