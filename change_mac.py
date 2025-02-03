import re
import subprocess
import sys
import logging
import os  # Added missing import
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mac_change.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_os():
    """Detect the operating system."""
    if sys.platform.startswith('linux'):
        return 'linux'
    elif sys.platform.startswith('darwin'):
        return 'macos'
    elif sys.platform.startswith('win'):
        return 'windows'
    else:
        logging.error("Unsupported operating system.")
        sys.exit(1)

def get_interfaces():
    """Detect available network interfaces."""
    os_type = get_os()
    interfaces = []

    if os_type == 'linux' or os_type == 'macos':
        try:
            output = subprocess.check_output(["ifconfig"]).decode()
            interfaces = re.findall(r'^\w+', output, re.MULTILINE)
        except Exception as e:
            logging.error(f"Error detecting interfaces: {e}")
            sys.exit(1)
    elif os_type == 'windows':
        try:
            output = subprocess.check_output(["ipconfig"]).decode()
            interfaces = re.findall(r'^Ethernet adapter (.+):', output, re.MULTILINE)
        except Exception as e:
            logging.error(f"Error detecting interfaces: {e}")
            sys.exit(1)

    if not interfaces:
        logging.error("No network interfaces found.")
        sys.exit(1)

    return interfaces

def get_current_mac(interface):
    """Get the current MAC address of the specified interface."""
    os_type = get_os()
    try:
        if os_type == 'linux' or os_type == 'macos':
            output = subprocess.check_output(["ifconfig", interface]).decode()
            mac_match = re.search(r'ether ([\da-fA-F:]{17})', output)
            if mac_match:
                return mac_match.group(1)
        elif os_type == 'windows':
            output = subprocess.check_output(["getmac", "/FO", "CSV", "/V"]).decode()
            for line in output.splitlines():
                if interface in line:
                    mac_match = re.search(r'([\da-fA-F-]{17})', line)
                    if mac_match:
                        return mac_match.group(1).replace('-', ':')
    except Exception as e:
        logging.error(f"Error getting MAC address: {e}")
    return None

def validate_mac(mac):
    """Validate the MAC address format."""
    if re.match(r'^([\da-fA-F]{2}:){5}[\da-fA-F]{2}$', mac):
        return True
    return False

def change_mac(interface, new_mac):
    """Change the MAC address of the specified interface."""
    os_type = get_os()
    try:
        if os_type == 'linux':
            subprocess.run(["sudo", "ifconfig", interface, "down"], check=True)
            subprocess.run(["sudo", "ifconfig", interface, "hw", "ether", new_mac], check=True)
            subprocess.run(["sudo", "ifconfig", interface, "up"], check=True)
        elif os_type == 'macos':
            subprocess.run(["sudo", "ifconfig", interface, "ether", new_mac], check=True)
        elif os_type == 'windows':
            subprocess.run(["netsh", "interface", "set", "interface", interface, "newmac=" + new_mac], check=True)
        logging.info(f"MAC address changed to {new_mac} on {interface}.")
    except Exception as e:
        logging.error(f"Error changing MAC address: {e}")
        sys.exit(1)

def backup_mac(interface, backup_file):
    """Backup the current MAC address to a file."""
    current_mac = get_current_mac(interface)
    if current_mac:
        with open(backup_file, 'w') as f:
            f.write(current_mac)
        logging.info(f"Backed up MAC address {current_mac} to {backup_file}.")
    else:
        logging.error("Failed to backup MAC address.")

def restore_mac(interface, backup_file):
    """Restore the original MAC address from a backup file."""
    try:
        with open(backup_file, 'r') as f:
            original_mac = f.read().strip()
        if validate_mac(original_mac):
            change_mac(interface, original_mac)
            logging.info(f"Restored MAC address to {original_mac} on {interface}.")
        else:
            logging.error("Invalid MAC address in backup file.")
    except Exception as e:
        logging.error(f"Error restoring MAC address: {e}")

def check_permissions():
    """Check if the script is running with sufficient privileges."""
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        if os.geteuid() != 0:
            logging.error("This script requires root privileges. Please run with sudo.")
            sys.exit(1)
    elif sys.platform.startswith('win'):
        try:
            subprocess.check_output(["whoami", "/priv"], stderr=subprocess.PIPE)
        except Exception:
            logging.error("This script requires administrator privileges.")
            sys.exit(1)

def main():
    """Main function to execute the script."""
    check_permissions()

    # Detect available interfaces
    interfaces = get_interfaces()
    print("Available network interfaces:")
    for i, iface in enumerate(interfaces):
        print(f"{i + 1}. {iface}")
    choice = int(input("Select the interface to modify (1, 2, ...): ")) - 1
    interface = interfaces[choice]

    # Backup current MAC address
    backup_file = f"{interface}_mac_backup.txt"
    backup_mac(interface, backup_file)

    # Prompt for new MAC address
    while True:
        new_mac = input("Enter the new MAC address (format: XX:XX:XX:XX:XX:XX): ").strip()
        if validate_mac(new_mac):
            break
        print("Invalid MAC address format. Please try again.")

    # Change MAC address
    change_mac(interface, new_mac)

    # Confirm new MAC address
    current_mac = get_current_mac(interface)
    if current_mac == new_mac:
        print(f"Success! MAC address changed to {current_mac}.")
    # else:
    #     print("Failed to change MAC address.")

    # Restore option
    if input("Do you want to restore the original MAC address? (y/n): ").lower() == 'y':
        restore_mac(interface, backup_file)

if __name__ == "__main__":
    main()
