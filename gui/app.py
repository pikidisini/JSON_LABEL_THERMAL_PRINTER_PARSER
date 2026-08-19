"""
GUI Application Entrypoint.
Launches the Desktop Label Preview & Inspector application.
"""

import sys
from gui.main_window import MainWindow


def main():
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
