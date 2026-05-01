import os
import shutil
from typing import Iterable


def _candidate_roots() -> Iterable[str]:
    if os.name == "nt":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            root = f"{letter}:\\"
            if os.path.exists(root):
                yield root
        return

    yield "/"


def check_disk():
    reports = []

    for root in _candidate_roots():
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue

        total_gb = usage.total / (1024 ** 3)
        used_gb = (usage.total - usage.free) / (1024 ** 3)
        free_gb = usage.free / (1024 ** 3)
        used_pct = 0 if usage.total == 0 else (used_gb / total_gb) * 100
        reports.append(
            f"{root} Total: {total_gb:.2f} GB | "
            f"Used: {used_gb:.2f} GB ({used_pct:.1f}%) | "
            f"Free: {free_gb:.2f} GB"
        )

    if not reports:
        return "No readable disks found."

    return "Disk usage:\n" + "\n".join(reports)
