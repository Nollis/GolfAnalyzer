import shutil
import os

def move_asset():
    src = "3DModel"
    dst = os.path.join("frontend", "static", "3DModel")
    
    if not os.path.exists(src):
        print(f"❌ Source {src} does not exist")
        return

    if os.path.exists(dst):
        print(f"⚠️ Destination {dst} already exists. Removing it first.")
        shutil.rmtree(dst)

    try:
        shutil.move(src, dst)
        print(f"✅ Successfully moved {src} to {dst}")
    except Exception as e:
        print(f"❌ Failed to move: {e}")

if __name__ == "__main__":
    move_asset()
