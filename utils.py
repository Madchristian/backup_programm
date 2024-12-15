import os

def ensure_directories_exist(path_list):
    for path in path_list:
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
