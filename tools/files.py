import os


LARGE_FILE_THRESHOLD_BYTES = 100 * 1024 * 1024
MAX_RESULTS = 10


def _scan_roots():
    roots = []
    home = os.path.expanduser("~")

    for name in ("Desktop", "Documents", "Downloads", "Videos"):
        path = os.path.join(home, name)
        if os.path.isdir(path):
            roots.append(path)

    if not roots:
        roots.append(os.getcwd())

    return roots


def find_large_files():
    matches = []

    for base_path in _scan_roots():
        for root, dirs, files in os.walk(base_path, topdown=True):
            dirs[:] = [
                directory
                for directory in dirs
                if not directory.startswith(".")
            ]
            for name in files:
                file_path = os.path.join(root, name)
                try:
                    size = os.path.getsize(file_path)
                except OSError:
                    continue

                if size >= LARGE_FILE_THRESHOLD_BYTES:
                    matches.append((size, file_path))

    if not matches:
        return "No files larger than 100 MB were found in common user folders."

    matches.sort(reverse=True)
    lines = []
    for size, file_path in matches[:MAX_RESULTS]:
        lines.append(f"{size / (1024 ** 2):.2f} MB - {file_path}")

    return "Large files:\n" + "\n".join(lines)
