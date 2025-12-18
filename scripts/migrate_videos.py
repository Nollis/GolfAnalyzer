import os
import shutil

SOURCE = "videos"
DEST = "storage/videos"

def migrate():
    print(f"Current CWD: {os.getcwd()}")
    
    if not os.path.exists(SOURCE):
        print(f"Source {SOURCE} does not exist!")
        return

    os.makedirs(DEST, exist_ok=True)
    print(f"Created/Verified {DEST}")
    
    files = [f for f in os.listdir(SOURCE) if os.path.isfile(os.path.join(SOURCE, f))]
    print(f"Found {len(files)} files in {SOURCE}")
    
    count = 0
    for f in files:
        src = os.path.join(SOURCE, f)
        dst = os.path.join(DEST, f)
        try:
            shutil.move(src, dst)
            count += 1
        except Exception as e:
            print(f"Error moving {f}: {e}")
            
    print(f"Successfully moved {count} files to {DEST}")

if __name__ == "__main__":
    migrate()
