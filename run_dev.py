"""Development runner with hot-reload support."""
import subprocess
import sys
import os


def main():
    """Run the app in development mode."""
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    # Run main.py with python
    subprocess.run([sys.executable, "main.py"], cwd=os.path.dirname(__file__))


if __name__ == "__main__":
    main()
