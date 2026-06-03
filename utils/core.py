import os
import sys


def get_full_path():
    if sys.platform == "win32":
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            system_path, _ = winreg.QueryValueEx(key, "Path")

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                user_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                user_path = ""

        separator = ";"

        # Combine registry paths with the bot's path and deduplicating it
        all_paths = os.environ["Path"].split(";") + system_path.split(";") + user_path.split(";")
    else:
        # On Unix the PATH is already full
        separator = ":"
        all_paths = os.environ["PATH"].split(separator)

        extra_paths = [
            "usr/local/bin",
            "/usr/bin",
            "/bin",
            "/usr/local/sbin",
            "/usr/sbin",
            "/sbin",
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/Library/Python/bin"),
        ]
        all_paths += extra_paths

    seen = set()
    deduped = []
    for p in all_paths:
        if p and p not in seen:
            seen.add(p)
            deduped.append(p)

    return separator.join(deduped)
