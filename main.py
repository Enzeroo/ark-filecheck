from pathlib import Path
import winreg
import os
import sys
import shutil
import ctypes
import time
import subprocess
import win32evtlog

CHEAT_FILENAMES = [
    "unleashed", "client_26", "client_27", "client_28", "client_29", "client_30", "client_31", "client_32", # unleashed
    "headshot", "hs", "hsloader", "hshider", "headshothider", # headshot
    "primal", # primal
    "addicted", # addicted
    "weedmen55", # weedmen
    "erge", # erge

    # others that could get flagged in a file check
    "cheat",
    "loader",
    "esp",
    "uwp",
    "inject"
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
    "UAS": {"hive": winreg.HKEY_CURRENT_USER,"path": r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"}
}

BROWSERS = {
    # browsers for downloads
    "CHROME": [r"%localappdata%\Google\Chrome\User Data\Default\History"],
    "EDGE": [r"%localappdata%\Microsoft\Edge\User Data\Default\History"],
    "FIREFOX": [r"%appdata%\Mozilla\Firefox\Profiles"]
}



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
                                print(f'Deleting: "{file.name}"')
                                try:
                                    file.unlink()
                                    pass
                                except Exception as er:
                                    print(f"Failed to delete {file.name}: {er}")
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
        print(f"Folder does not exist: {folder_path}")
        return

    for item in folder_path.iterdir():
        if item.name.lower() not in [name.lower() for name in AC_FILES]:
            print(f'Deleting: "{item.name}"')
            try:
                if item.is_file():
                    item.unlink() 
                elif item.is_dir():
                    shutil.rmtree(item)
            except Exception as er:
                print(f"Failed to delete {item.name}: {er}")

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
                        print(f'Deleting registry value: "{value_name}"')
                        try:
                            winreg.DeleteValue(key, value_name)
                            pass
                        except Exception as er:
                            print(f"Failed to delete {value_name}: {er}")
                        break

    except FileNotFoundError:
        print(f"Key not found: {key_path}")

def cleanBrowserHistory():
    edge = BROWSERS["EDGE"][0]
    chrome = BROWSERS["CHROME"][0]
    firefox = BROWSERS["FIREFOX"][0]

    chrome_db = Path(os.path.expandvars(chrome))
    if chrome_db.exists():
        print(f"Deleting chrome database: {chrome_db}")
        chrome_db.unlink()

    edge_db = Path(os.path.expandvars(edge))
    if edge_db.exists():
        print(f"Deleting edge database: {edge_db}")
        edge_db.unlink()

    firefox_root = Path(os.path.expandvars(firefox))
    if firefox_root.exists():
        for profile in firefox_root.iterdir():
            places_db = profile / "places.sqlite"
            if places_db.exists():
                print(f"Deleting firefox database: {places_db}")
                places_db.unlink()

def closeBrowser(process_name):
    for _ in range(3):
        subprocess.run(['taskkill', '/f', '/im', process_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.5)

def cleanCrashes():
    path = FILE_PATHS["CRASHDUMP_ARCHIVE"][0]
    crashdump_path = Path(os.path.expandvars(path))

    if not crashdump_path.exists():
        print(f"Folder does not exist: {crashdump_path}")
        return

    for file in crashdump_path.iterdir():
        if file.is_file():
            try:
                print(f"Deleting: {file}")
                file.unlink()
            except Exception as er:
                print(f"Failed to delete {file}: {er}")
        elif file.is_dir():
            try:
                print(f"Deleting folder: {file}")
                shutil.rmtree(file)
            except Exception as er:
                print(f"Failed to delete folder {file}: {er}")

def cleanEventLog(log_name):
    server = 'localhost'
    flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    try:
        hand = win32evtlog.OpenEventLog(server, log_name)
        total = win32evtlog.GetNumberOfEventLogRecords(hand)
        print(f"Total event log records: {total}")

        events = True
        while events:
            records = win32evtlog.ReadEventLog(hand, flags, 0)
            if not records:
                break

            for record in records:
                msg = str(record.StringInserts) if record.StringInserts else ""
                msg_lower = msg.lower()
                if any(word in msg_lower for word in CHEAT_FILENAMES):
                    print(f"Deleting event {record.EventID}: {msg}")
                    try:
                        win32evtlog.ClearEventLog(hand, None)
                    except Exception as e:
                        print(f"Failed to delete event: {e}")

        win32evtlog.CloseEventLog(hand)

    except Exception as e:
        print(f"Failed to open event log {log_name}: {e}")





def admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == "__main__":
    # run as admin for all permissions
    if not admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    try:
        cleanFiles()
        print("")
        cleanAC()
        print("")

        cleanRegistry("UAC")
        cleanRegistry("UAS")
        cleanRegistry("MUI")
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
        print("")

        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x1 | 0x2 | 0x4)
        print("Recycle bin emptied")
        print("")

    except Exception as e:
        print(f"Error: {e}")

    input("Press any key to delete this file")
    print("")
    print("Miss you already \3")

    time.sleep(3)
    file_path = os.path.abspath(sys.argv[0])
    # cmd waits a little to allow current process to exit, then deletes file
    cmd = f'cmd /c ping 127.0.0.1 -n 3 > nul & del "{file_path}"'
    subprocess.Popen(cmd, shell=True)


