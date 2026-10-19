"""
create_desktop_shortcut.py - makes a desktop shortcut for the public website.

Run it once:
    venv311\\Scripts\\python.exe create_desktop_shortcut.py

After that, double-click "Baby Monitor - Public Website" on your desktop.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
SHORTCUT = os.path.join(DESKTOP, "Baby Monitor - Public Website.lnk")
TARGET = os.path.join(HERE, "venv311", "Scripts", "python.exe")
SCRIPT = os.path.join(HERE, "public_website.py")
ICON = os.path.join(HERE, "dist", "BabyMonitor", "BabyMonitor.exe")


def main():
    if not os.path.isfile(TARGET):
        print("Could not find the Python environment:")
        print("  %s" % TARGET)
        print("Run this script from the project folder.")
        return 1

    if not os.path.isdir(DESKTOP):
        print("Could not find the Desktop folder at:")
        print("  %s" % DESKTOP)
        return 1

    try:
        import win32com.client
    except ImportError:
        print("pywin32 is needed to create the shortcut.")
        print("Installing it ...")
        os.system(
            '"%s" -m pip install pywin32' % os.path.join(HERE, "venv311", "Scripts", "python.exe")
        )
        try:
            import win32com.client
        except ImportError:
            print("Could not install pywin32. Run this script again.")
            return 1

    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(SHORTCUT)
    shortcut.Targetpath = TARGET
    shortcut.Arguments = '"%s"' % SCRIPT
    shortcut.WorkingDirectory = HERE
    shortcut.Description = "Baby Monitoring System - public website"
    if os.path.isfile(ICON):
        shortcut.IconLocation = ICON + ",0"
    shortcut.save()

    print("Shortcut created:")
    print("  %s" % SHORTCUT)
    print()
    print("Double-click it to start the public website.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
