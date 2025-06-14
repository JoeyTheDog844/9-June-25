import subprocess
import datetime
import socket
import re
import winreg

def clean_output(text):
    # Remove all non-ASCII printable characters (except newline)
    return re.sub(r'[^\x20-\x7E\n]', '', text)

def get_antivirus_status():
    try:
        # ✅ Get installed antivirus from Windows Security Center
        cmd = 'powershell -Command "Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntivirusProduct | Select-Object -ExpandProperty displayName"'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

        if not output:
            return "No antivirus detected (Windows Defender may be inactive or another AV is in use)"

        antivirus_list = [av.strip() for av in output.split("\n") if av.strip()]
        return f"{', '.join(antivirus_list)}"

    except Exception as e:
        return f"Error retrieving antivirus status: {e}"

def get_last_scan_time():
    try:
        # ✅ First, check if Windows Defender is running
        cmd1 = 'powershell -Command "(Get-MpComputerStatus).AMRunningMode"'
        defender_mode = subprocess.check_output(cmd1, shell=True).decode('utf-8').strip()

        if "Passive" in defender_mode:
            return "Windows Defender is in Passive Mode (Another antivirus is active)"

        # ✅ Check Last Scan Time (First Try Standard Method)
        cmd2 = 'powershell -Command "(Get-MpComputerStatus).ScanTime"'
        output = subprocess.check_output(cmd2, shell=True).decode('utf-8').strip()

        if output:
            return f"{output}"

        # ✅ If Standard Method Fails, Check Event Logs
        cmd3 = 'powershell -Command "Get-WinEvent -LogName \'Microsoft-Windows-Windows Defender/Operational\' | Where-Object Id -eq 1001 | Select-Object -First 1 -ExpandProperty TimeCreated"'
        output = subprocess.check_output(cmd3, shell=True).decode('utf-8').strip()

        if output:
            return f"{output}"

        return "Windows Defender inactive or not scanning"

    except Exception as e:
        return f"Error retrieving scan time: {e}"

def get_usb_device_control_status():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\USBSTOR") as key:
            value, _ = winreg.QueryValueEx(key, "Start")
            if value == 4:
                return "USB Access: Blocked"
            elif value in [0, 1, 2, 3]:
                return "USB Access: Allowed"
            else:
                return f"USB Access: Unknown (Start = {value})"
    except Exception as e:
        return f"Error checking USB storage access: {e}"

def get_autoplay_status():
    try:
        path1 = r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
        path2 = r"Software\Microsoft\Windows\CurrentVersion\Explorer\AutoplayHandlers"

        val1 = val2 = None

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path1) as key:
                val1, _ = winreg.QueryValueEx(key, "NoDriveTypeAutoRun")
        except FileNotFoundError:
            pass

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path2) as key:
                val2, _ = winreg.QueryValueEx(key, "DisableAutoplay")
        except FileNotFoundError:
            pass

        # New logic: if either setting disables autoplay, return disabled
        if val1 == 255 or val2 == 1:
            return "AutoPlay is Disabled"
        elif val1 is None and val2 is None:
            return "AutoPlay status unknown (both keys missing)"
        else:
            return "AutoPlay is Enabled"

    except Exception as e:
        return f"Error checking AutoPlay status: {e}"

def get_rdp_status():
    try:
        cmd = 'powershell -Command "(Get-ItemProperty -Path \'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server\').fDenyTSConnections"'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

        if output == "1":
            return "Disabled (RDP is OFF)"
        elif output == "0":
            return "Enabled (RDP is ON)"
        else:
            return f"RDP status unknown: {output}"

    except Exception as e:
        return f"Error retrieving RDP status: {e}"

def get_telnet_status():
    try:
        cmd = 'powershell -Command "Get-Service -Name Telnet | Select-Object -ExpandProperty Status"'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

        if output.lower() == "stopped":
            return "Disabled"
        elif output.lower() == "running":
            return "Enabled (Insecure)"
        else:
            return f"Telnet status unknown: {output}"

    except subprocess.CalledProcessError:
        return "Not Installed"

def get_default_share_status():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters")
        value, _ = winreg.QueryValueEx(key, "AutoShareWks")
        if value == 0:
            return "Disabled (Safe)"
        else:
            return "Enabled (Security Risk)"
    except FileNotFoundError:
        # Key doesn't exist — by default, admin shares are enabled
        return "Enabled (Security Risk)"
    except Exception as e:
        return f"Error reading Default Share status: {e}"

def get_shared_folder_status():
    try:
        cmd = 'powershell -Command "Get-SmbShare | Where-Object {$_.Name -notmatch \'^\\w+\\$$\'} | Select-Object -ExpandProperty Name"'
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8').strip()

        if "is not recognized" in output or "not found" in output.lower():
            return "Error: Get-SmbShare not available"

        if output:
            return f"Configured (Security Risk) - {output}"
        else:
            return "Not Configured (Safe)"

    except subprocess.CalledProcessError as e:
        return f"Error retrieving Shared Folder status:\n{e.output.decode('utf-8')}"

def get_bios_password_status():
    return "Manual Check Required"

def check_browser_saved_passwords():
    return "Manual Check Required"

def get_login_password_status():
    try:
        # ✅ Get the current logged-in Windows user
        cmd_user = 'powershell -Command "$env:USERNAME"'
        username = subprocess.check_output(cmd_user, shell=True).decode('utf-8').strip()

        # ✅ Check if the user has a password set
        cmd_password = f'net user "{username}"'
        output = subprocess.check_output(cmd_password, shell=True).decode('utf-8')

        for line in output.splitlines():
            if "Password required" in line:
                if "Yes" in line:
                    return f"Windows Login Password Set (User: {username})"
                elif "No" in line:
                    return f"No Windows Login Password (User: {username})"
                else:
                    return f"Windows Login Password line unclear: {line.strip()}"

        return f"Windows Login Password Status Unknown (User: {username})"

    except Exception as e:
        return f"Error Retrieving Windows Login Password Status: {e}"

def get_password_policy_status():
    try:
        cmd = 'powershell -Command "net accounts | Select-String \'password\'"'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
        output = clean_output(output)

        min_length = None
        min_age = None
        max_age = None

        if "Minimum password length:" in output:
            min_length = int(output.split("Minimum password length:")[1].split("\n")[0].strip())

        if "Minimum password age (days):" in output:
            min_age = int(output.split("Minimum password age (days):")[1].split("\n")[0].strip())

        if "Maximum password age (days):" in output:
            max_age = int(output.split("Maximum password age (days):")[1].split("\n")[0].strip())

        if min_length == 10 and min_age == 0 and max_age == 45:
            return "Password Policy is Properly Configured"
        elif min_length == 0:
            return "Weak Password Policy (Minimum length is 0)"
        else:
            return "Partial Password Policy (Doesn't match standard)"

    except Exception as e:
        return f"Error Retrieving Password Policy: {e}"

def get_lockout_policy_status():
    try:
        # Run PowerShell command to extract lockout-related lines from `net accounts`
        cmd = 'powershell -Command "net accounts | Select-String \'Lockout\'"'
        output = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()

        lockout_threshold = "Unknown"

        # Loop through each line of output to find the threshold
        for line in output.split("\n"):
            if "Lockout threshold" in line:
                lockout_threshold = line.split(":")[-1].strip()

        # Interpret the result
        if lockout_threshold.lower() == "never":
            return "No Lockout Policy (Accounts never lock)"
        else:
            return "Lockout Policy is Configured"

    except Exception as e:
        return f"Error Retrieving Lockout Policy: {str(e)}"

def get_firewall_status():
    try:
        cmd = 'powershell -Command "Get-NetFirewallProfile | Select-Object -Property Name, Enabled"'
        result = subprocess.check_output(cmd, shell=True, text=True).strip()

        profile_statuses = []
        for line in result.splitlines():
            if "Domain" in line:
                profile = "Domain"
            elif "Private" in line:
                profile = "Private"
            elif "Public" in line:
                profile = "Public"
            else:
                continue

            status = "Enabled" if "True" in line else "Disabled"
            profile_statuses.append(f"{profile} Profile: {status}")

        return "\n".join(profile_statuses) if profile_statuses else "Could not determine Firewall status"

    except Exception as e:
        return f"Error retrieving Firewall status: {e}"

def generate_security_log():
    # Gather all required data
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    antivirus_status = get_antivirus_status()
    firewall_status = get_firewall_status()
    scan_time = get_last_scan_time()
    usb_status = get_usb_device_control_status()
    autoplay_status = get_autoplay_status()
    rdp_status = get_rdp_status()
    telnet_status = get_telnet_status()
    default_share_status = get_default_share_status()
    shared_folders_status = get_shared_folder_status()
    bios_password_status = get_bios_password_status()
    browser_password_status = check_browser_saved_passwords()
    login_password_status = get_login_password_status()
    password_policy_status = get_password_policy_status()
    System_lockout_policy_status = get_lockout_policy_status()

    log_entry = f"""
📌 [Antivirus Security Log]
-------------------------------------
Timestamp: {timestamp}

{antivirus_status}

Windows Firewall Status:
{firewall_status}

Last Windows Defender Scan Time: {scan_time}

{usb_status}

AutoPlay Status: {autoplay_status}

Remote Desktop Protocol (RDP): {rdp_status}

Telnet: {telnet_status}

Default Share: {default_share_status}

Shared Folders: {shared_folders_status}

BIOS Password: {bios_password_status}

Saved Browser Passwords: {browser_password_status}

{login_password_status}

Password Policy: {password_policy_status}

System Lockout Policy: {System_lockout_policy_status}

-------------------------------------
"""

    # Save to log file
    with open("security_logs.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry + "\n")

    print(log_entry)

if __name__ == "__main__":
    generate_security_log()
