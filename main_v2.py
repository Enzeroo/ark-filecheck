from pathlib import Path
import winreg
import os
import sys
import shutil
import ctypes
import time
import subprocess
import win32evtlog
from concurrent.futures import ThreadPoolExecutor


SKIP_DIR_NAMES = {
    "Windows",
    "Program Files",
    "Program Files (x86)",
    "$Recycle.Bin",
    "System Volume Information"
}

CHEAT_FILENAMES = [
    "unleashed", "client_26", "client_27", "client_28", "client_29", "client_30", "client_31", "client_32", # unleashed
    "headshot", "hs", "hsloader", "hshider", "headshothider", # headshot
    "primal", # primal
    "addicted", # addicted
    "weedmen55", # weedmen
    "erge", # erge
    "crumb", # some shit i found idk

    # others that could get flagged in a file check
    "cheat",
    "esp",
    "inject",
    "cetrainer"
]

AC_FILES = [
    "temp",
    "microsoft",
    "arkholes",
    "INetCache",
    "INetCookies",
    "INetHistory"
]

FILE_PATHS = {
    # prefetch for windows saving configs kinda
    "PREFETCH": [r"C:\Windows\Prefetch"],
    # localappdata for where most cheats hide configs
    "ARK_AC": [r"%localappdata%\Packages\StudioWildcard.4558480580BB9_1w2mm55455e38\AC"],
    # temp for some loaders and configs
    "TEMP": [r"%TEMP%"],
    # specific for headshot only where files are saved
    "HS_TEMP": [r"%TEMP%\bin_files"],
    # ark temp for icons
    "ARK_TEMP": [r"%localappdata%\Packages\StudioWildcard.4558480580BB9_1w2mm55455e38\TempState"],
    # windows saves crashes into a specific folder 
    "REPORT_ARCHIVE": [r"C:\ProgramData\Microsoft\Windows\WER\ReportArchive"],
    # more crashdump archives
    "CRASHDUMP_ARCHIVE": [r"%localappdata%\CrashDumps"],
    # recent windows files opened (i think??)
    "RECENT_ARCHIVE": [r"%appdata%\Microsoft\Windows\Recent"],
    # user downloads
    "DOWNLOADS": [r"%userprofile%\Downloads"]
}

REGISTRY = {
    # names for all exes run
    "MUI": {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Classes\Local Settings\Software\Microsoft\Windows\Shell\MuiCache"},
    # apps that need UAC
    "UAC": {"hive": winreg.HKEY_CURRENT_USER,"path": r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Compatibility Assistant\Store"},
    # what apps were run
    "UAS": {"hive": winreg.HKEY_CURRENT_USER,"path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"},
    # all lists of what certain file extension things run
    "BMRU": {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\Shell\BagMRU"},
    "BAG": {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\Shell\Bags"},
    "LVP": {"hive": winreg.HKEY_CURRENT_USER, "path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\ComDlg32\LastVisitedPidlMRU"},
}

BROWSERS = {
    # browsers for downloads
    "CHROME": [r"%localappdata%\Google\Chrome\User Data\Default\History"],
    "EDGE": [r"%localappdata%\Microsoft\Edge\User Data\Default\History"],
    "FIREFOX": [r"%appdata%\Mozilla\Firefox\Profiles"]
}


def cleanAllFiles():

    print("Searching through all files, this will take a while")
    def process_file(path):
        try:
            name = os.path.basename(path).lower()

            if not name.endswith(".exe"):
                return

            if any(term in name for term in CHEAT_FILENAMES):
                print(f"Deleting {path}")
                os.remove(path)

        except Exception:
            pass

    def scan_drive(drive):
        if drive == "C:\\":
            start_paths = ["C:\\Users"]
        else:
            start_paths = [drive]

        with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
            for start in start_paths:
                for root, dirs, files in os.walk(start):
                    dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]

                    for file in files:
                        full_path = os.path.join(root, file)
                        executor.submit(process_file, full_path)

    drives = [
        f"{letter}:\\"
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if os.path.exists(f"{letter}:\\")
    ]

    for drive in drives:
        print(f"Scanning {drive}")
        scan_drive(drive)


def cleanFiles():
    for folder_list in FILE_PATHS.values():
        for folder in folder_list:
            folder_path = Path(os.path.expandvars(folder))
            if not folder_path.exists():
                continue

            if folder_path.is_dir():
                for file in folder_path.iterdir():
                    if file.is_file():
                        file_lower = file.name.lower()
                        for cheat in CHEAT_FILENAMES:
                            if cheat.lower() in file_lower:
                                print(f'Deleting "{file.name}"')
                                try:
                                    file.unlink()
                                    pass
                                except Exception as er:
                                    print(f"Failed to delete {file.name} {er}")
                                break

            elif folder_path.is_file():
                file_lower = folder_path.name.lower()
                for cheat in CHEAT_FILENAMES:
                    if cheat.lower() in file_lower:
                        print(f'Deleting: "{folder_path.name}"')
                        try:
                            folder_path.unlink()
                        except Exception as er:
                            print(f"Failed to delete {folder_path.name}: {er}")
                        break


def cleanAC():
    raw_path = FILE_PATHS["ARK_AC"][0]
    folder_path = Path(os.path.expandvars(raw_path))
    if not folder_path.exists():
        print(f"Folder {folder_path} does not exist")
        return

    for item in folder_path.iterdir():
        if item.name.lower() not in [name.lower() for name in AC_FILES]:
            print(f'Deleting "{item.name}"')
            try:
                if item.is_file():
                    item.unlink() 
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as er:
                print(f"Failed to delete {item.name} {er}")


def cleanRegistry(name):
    reg = REGISTRY.get(name)

    hive = reg["hive"]
    key_path = reg["path"]

    try:
        with winreg.OpenKey(hive, key_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            i = 0
            value_names = []
            while True:
                try:
                    value_name, value_data, value_type = winreg.EnumValue(key, i)
                    value_names.append(value_name)
                    i += 1
                except OSError:
                    break

            for value_name in value_names:
                value_lower = value_name.lower()
                for cheat in CHEAT_FILENAMES:
                    if cheat.lower() in value_lower:
                        print(f'Deleting registry "{value_name}"')
                        try:
                            winreg.DeleteValue(key, value_name)
                            pass
                        except Exception as er:
                            print(f"Failed to delete {value_name} {er}")
                        break

    except FileNotFoundError:
        print(f"Key not found: {key_path}")


def cleanUserAssist():
    # i despise registry so this is NOT my code
    reg = REGISTRY.get("UAS")
    hive = reg["hive"]
    path = reg["path"]

    try:
        with winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE) as key:
            i = 0
            while True:
                try:
                    guid = winreg.EnumKey(key, i)
                    with winreg.OpenKey(key, guid, 0, winreg.KEY_WRITE) as guid_key:
                        while True:
                            try:
                                value_name = winreg.EnumValue(guid_key, 0)[0]
                                winreg.DeleteValue(guid_key, value_name)
                            except OSError:
                                break
                    i += 1
                except OSError:
                    break
        print("UserAssist history cleared")
    except Exception as e:
        print(e)


def cleanShellBags():
    # more slop
    keys = ["BMRU", "BAG", "LVP"]
    print("Wiping shellbags etc")

    for key_name in keys:
        reg = REGISTRY.get(key_name)

        hive = reg["hive"]
        path = reg["path"]

        try:
            parent_key = winreg.OpenKey(hive, path, 0, winreg.KEY_WRITE)
            subkey_names = []
            try:
                i = 0
                while True:
                    subkey_name = winreg.EnumKey(parent_key, i)
                    subkey_names.append(subkey_name)
                    i += 1
            except OSError:
                pass
            
            for subkey_name in subkey_names:
                full_subkey_path = f"{path}\\{subkey_name}"
                try:
                    winreg.DeleteKey(hive, full_subkey_path)
                except FileNotFoundError:
                    pass

            value_names = []
            try:
                i = 0
                while True:
                    value_name = winreg.EnumValue(parent_key, i)
                    value_names.append(value_name)
                    i += 1
            except OSError:
                pass

            for value_name in value_names:
                try:
                    winreg.DeleteValue(parent_key, value_name)
                except Exception as e:
                    print(e)

            winreg.CloseKey(parent_key)

        except FileNotFoundError:
            print(f"Registry key not found")
        except Exception as e:
            print(e)

    print("Finished wiping ShellBags")


def cleanBrowserHistory():
    edge = BROWSERS["EDGE"][0]
    chrome = BROWSERS["CHROME"][0]
    firefox = BROWSERS["FIREFOX"][0]

    chrome_db = Path(os.path.expandvars(chrome))
    if chrome_db.exists():
        print(f"Deleting {chrome_db}")
        chrome_db.unlink()

    edge_db = Path(os.path.expandvars(edge))
    if edge_db.exists():
        print(f"Deleting {edge_db}")
        edge_db.unlink()

    firefox_root = Path(os.path.expandvars(firefox))
    if firefox_root.exists():
        for profile in firefox_root.iterdir():
            places_db = profile / "places.sqlite"
            if places_db.exists():
                print(f"Deleting {places_db}")
                places_db.unlink()


def closeBrowser(process_name):
    for _ in range(3):
        subprocess.run(['taskkill', '/f', '/im', process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)


def cleanCrashes():
    path = FILE_PATHS["CRASHDUMP_ARCHIVE"][0]
    crashdump_path = Path(os.path.expandvars(path))

    if not crashdump_path.exists():
        print(f"{crashdump_path} does not exist")
        return

    for file in crashdump_path.iterdir():
        if file.is_file():
            try:
                print(f"Deleting file {file}")
                file.unlink()
            except Exception as er:
                print(f"Failed to delete file {file} {er}")
        elif file.is_dir():
            try:
                print(f"Deleting folder {file}")
                shutil.rmtree(file)
            except Exception as er:
                print(f"Failed to delete folder {file} {er}")


def cleanEventLog(log_name):
    try:
        hand = win32evtlog.OpenEventLog(None, log_name)
        win32evtlog.ClearEventLog(hand, None)
        win32evtlog.CloseEventLog(hand)
        print(f"Cleared event log: {log_name}")
    except Exception as e:
        print(e)




def admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    try:
        print("")
        cleanFiles()
        print("")
        cleanAC()
        print("")

        cleanRegistry("UAC")
        cleanRegistry("MUI")
        # had problems with it before
        # so it simply deletes all keys in userassist (safe)
        cleanUserAssist()
        print("")
        cleanShellBags()
        print("")

        # close all browsers
        closeBrowser("chrome.exe")
        closeBrowser("msedge.exe")
        closeBrowser("firefox.exe")

        cleanBrowserHistory()
        print("")

        hs_path = os.path.expandvars(FILE_PATHS["HS_TEMP"][0])
        if os.path.exists(hs_path):
            print(f"Deleting: {hs_path}")
            shutil.rmtree(hs_path)
            print("")

        cleanEventLog("Application")
        cleanEventLog("System")
        cleanEventLog("Security")
        print("")

        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x1 | 0x2 | 0x4)
        print("Recycle bin emptied")
        print("")

    except Exception as e:
        print(e)

    input("Press any key to delete this file")
    print("")
    print("Miss you already \3")

    time.sleep(3)
    file_path = os.path.abspath(sys.argv[0])
    # cmd waits a little to allow current process to exit, then deletes file
    cmd = f'cmd /c ping 127.0.0.1 -n 3 > nul & del "{file_path}"'
    subprocess.Popen(cmd, shell=True)


if __name__ == "__main__":
    # run as admin for all permissions
    if not admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()


    print("\n 1 -> Delete ALL cheat-related files on the pc")
    print("      WARNING - this will fuck up some of your actual programs,")
    print("                so run at great risk or use option 2 and ")
    print("                manually delete the actual cheat file(s)\n")
    print(" 2 -> Delete all cheat-related files BUT the actual .exe")
    option = int(input("\n Enter an option: "))
    if option == 1:
        print(" \nDeleting everything on the pc")
        cleanAllFiles()
        main()

    elif option == 2:
        print("\n Deleting everything but saving the actual loader")
        main()

    else:
        print("\n Fuck you")
        sys.exit()



