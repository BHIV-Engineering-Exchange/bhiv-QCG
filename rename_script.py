import os
import glob

REPLACEMENTS = {
    "Dhiraj": "External",
    "dhiraj": "external",
    "DHIRAJ": "EXTERNAL"
}

extensions = ["*.py", "*.md", "*.yaml", "*.json", "*.txt"]
files_to_check = []
for ext in extensions:
    files_to_check.extend(glob.glob(f"**/{ext}", recursive=True))

for filepath in files_to_check:
    filename = os.path.basename(filepath)
    new_filename = filename
    for old, new in REPLACEMENTS.items():
        new_filename = new_filename.replace(old, new)
        
    if new_filename != filename:
        new_filepath = os.path.join(os.path.dirname(filepath), new_filename)
        try:
            os.rename(filepath, new_filepath)
            print(f"Renamed {filepath} to {new_filepath}")
        except Exception as e:
            print(f"Failed to rename {filepath}: {e}")
