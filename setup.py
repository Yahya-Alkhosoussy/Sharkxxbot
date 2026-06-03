import subprocess
import sys


def install():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "certifi", "pip"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"])

    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("Setup complete!")


if __name__ == "__main__":
    install()
