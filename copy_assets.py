import shutil
import os

src_dir = r"C:\Users\niklasb\.gemini\antigravity\brain\1cfc7d47-f8d9-4875-8f1f-9448cb73abe9"
dst_dir = r"c:\Projekt\GolfAnalyzer\frontend\static\images"

files = {
    "hero_golfer_skeleton_1765700427051.png": "hero-golfer.png",
    "partner_gear_1765700914283.png": "partner-gear.png",
    "partner_fitness_1765700929375.png": "partner-fitness.png",
    "partner_coaching_1765700941887.png": "partner-coaching.png"
}

os.makedirs(dst_dir, exist_ok=True)

for src_name, dst_name in files.items():
    src = os.path.join(src_dir, src_name)
    dst = os.path.join(dst_dir, dst_name)
    try:
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {src_name} to {dst_name}")
        else:
            print(f"Source not found: {src}")
    except Exception as e:
        print(f"Failed to copy {src_name}: {e}")
