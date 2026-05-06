import os
import shutil
import datetime

def main():
    src = r"E:\Axiom"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"E:\Axiom_backup_{ts}"
    if not os.path.isdir(src):
        print(f"SOURCE not found: {src}")
        return
    # Ensure not to overwrite existing backup name
    if os.path.exists(dst):
        i = 1
        while True:
            alt = f"{dst}_{i:02d}"
            if not os.path.exists(alt):
                dst = alt
                break
            i += 1
    shutil.copytree(src, dst)
    print(f"Backup created: {dst}")

if __name__ == '__main__':
    main()
