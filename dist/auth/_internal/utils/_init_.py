import os

folders = [
    "core",
    "windows",
    "utils",
    "theme"
]

base_path = "/mnt/data/ProjectClubTest"
created = []

for folder in folders:
    folder_path = os.path.join(base_path, folder)
    init_file = os.path.join(folder_path, "__init__.py")
    os.makedirs(folder_path, exist_ok=True)
    with open(init_file, "w") as f:
        f.write("# Package init\n")
    created.append(init_file)

created
