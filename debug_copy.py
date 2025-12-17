import os
src_dir = r"C:\Users\niklasb\.gemini\antigravity\brain\1cfc7d47-f8d9-4875-8f1f-9448cb73abe9"
print(f"Checking {src_dir}")
try:
    files = os.listdir(src_dir)
    print(f"Found {len(files)} files.")
    for f in files:
        if "hero" in f or "partner" in f: print(f)
except Exception as e:
    print(f"Error listing: {e}")
