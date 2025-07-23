# Copyright Minimasoft (c) 2025

from pathlib import Path
from time import sleep


def main():
    print("holi")
    print(list(Path("/usr/bin").glob('*')))
    sleep(999)


if __name__ == "__main__":
    main()
