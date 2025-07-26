import os
import shutil

DEST_NAME = 'dist'
IGNORE_DIRS = [DEST_NAME, ".git"]

source_dir = os.getcwd()
destination_dir = os.path.join(source_dir, DEST_NAME)

# Create the destination directory if it doesn't exist
os.makedirs(destination_dir, exist_ok=True)

extensions = ['.bmp', '.tga', '.jpg']

for root, dirs, files in os.walk(source_dir):
    # remove dest from the pool of dirs
    print(f"PRE_DIR: {dirs}")
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
    print(f"POST_DIR: {dirs}")
    for file in files:
        if file.lower().endswith(tuple(extensions)):
            source_path = os.path.join(root, file)
            relative_path = os.path.relpath(root, source_dir)
            target_folder = os.path.join(destination_dir, relative_path)
            os.makedirs(target_folder, exist_ok=True)

            dest_path = os.path.join(target_folder, file)
            shutil.copy2(source_path, dest_path)
            print(f"Copied: {source_path} → {dest_path}")
