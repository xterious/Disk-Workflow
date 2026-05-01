import os
import shutil
import tempfile


def _temp_dirs():
    candidates = {
        tempfile.gettempdir(),
    }

    if os.name == "nt":
        local_app_data = os.environ.get("LOCALAPPDATA")
        windows_dir = os.environ.get("WINDIR", r"C:\Windows")

        if local_app_data:
            candidates.add(os.path.join(local_app_data, "Temp"))
        candidates.add(os.path.join(windows_dir, "Temp"))

    return [path for path in candidates if path and os.path.isdir(path)]


def _dir_size_bytes(path):
    total = 0
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [directory for directory in dirs if not os.path.islink(os.path.join(root, directory))]
        for name in files:
            file_path = os.path.join(root, name)
            if os.path.islink(file_path):
                continue
            try:
                total += os.path.getsize(file_path)
            except OSError:
                continue
    return total


def get_temp_size():
    paths = _temp_dirs()
    if not paths:
        return "No temp directories found."

    total = sum(_dir_size_bytes(path) for path in paths)
    details = [f"{path}" for path in paths]
    return (
        f"Reclaimable temp/cache space: {total / (1024 ** 2):.2f} MB\n"
        f"Scanned:\n" + "\n".join(details)
    )


def clean_temp():
    paths = _temp_dirs()
    if not paths:
        return "No temp directories found."

    deleted_files = 0
    deleted_dirs = 0
    errors = 0

    for base_path in paths:
        try:
            entries = os.listdir(base_path)
        except OSError:
            errors += 1
            continue

        for entry in entries:
            target = os.path.join(base_path, entry)
            try:
                if os.path.isdir(target) and not os.path.islink(target):
                    shutil.rmtree(target)
                    deleted_dirs += 1
                else:
                    os.remove(target)
                    deleted_files += 1
            except OSError:
                errors += 1

    return (
        f"Temp cleanup completed. Deleted files: {deleted_files}, "
        f"deleted directories: {deleted_dirs}, errors: {errors}"
    )
