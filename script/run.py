#!/opt/core/venv/bin/python3
import os
import subprocess
import sys
import time
import signal
import glob
from pathlib import Path

from core.emulator.coreemu import CoreEmu
from core.emulator.enumerations import EventTypes
from core.nodes.base import CoreNode

# Global variables
XML_FILE = None
LOG_DIR = None
coreemu = None
session = None

def cleanup_processes():
    """Kill all CORE and REC processes"""
    subprocess.run(["pkill", "-9", "-f", "dtnd"], capture_output=True)
    subprocess.run(["pkill", "-9", "-f", "rec.run_dtn"], capture_output=True)

def stop(sig=None, frame=None):
    global coreemu, session
    
    print("\n\nCollecting logs...")
    
    # Create logs directory
    LOG_DIR.mkdir(exist_ok=True)
    
    # Collect broker logs separately (keep each node's log separate)
    broker_files = glob.glob("/tmp/rec_broker_B*.log")
    broker_files.sort()
    
    for log_file in broker_files:
        src_path = Path(log_file)
        # Extract node identifier (e.g., B1, B2, B3)
        node_id = src_path.stem.replace("rec_broker_", "")
        dst_path = LOG_DIR / f"rec_broker_{node_id}.txt"
        
        # Copy log file
        with open(src_path, "r") as src, open(dst_path, "w") as dst:
            dst.write(src.read())
    
    if broker_files:
        print(f"✓ Collected {len(broker_files)} broker logs separately")
    
    # Collect datastore logs separately (keep each node's log separate)
    datastore_files = glob.glob("/tmp/rec_datastore_D*.log")
    datastore_files.sort()
    
    for log_file in datastore_files:
        src_path = Path(log_file)
        # Extract node identifier (e.g., D1, D2, D3, D4, D5)
        node_id = src_path.stem.replace("rec_datastore_", "")
        dst_path = LOG_DIR / f"rec_datastore_{node_id}.txt"
        
        # Copy log file
        with open(src_path, "r") as src, open(dst_path, "w") as dst:
            dst.write(src.read())
    
    if datastore_files:
        print(f"✓ Collected {len(datastore_files)} datastore logs separately")
    
    # Collect client logs separately
    client_files = glob.glob("/tmp/rec_client_Cl*.log")
    client_files.sort()
    
    for log_file in client_files:
        src_path = Path(log_file)
        # Extract node identifier (e.g., Cl)
        node_id = src_path.stem.replace("rec_client_", "")
        dst_path = LOG_DIR / f"rec_client_{node_id}.txt"
        
        # Copy log file
        with open(src_path, "r") as src, open(dst_path, "w") as dst:
            dst.write(src.read())
    
    if client_files:
        print(f"✓ Collected {len(client_files)} client logs separately")
    
    # Change file owner from root to user
    user_id = int(os.environ.get('SUDO_UID', os.getuid()))
    group_id = int(os.environ.get('SUDO_GID', os.getgid()))
    
    txt_files = LOG_DIR.glob("*.txt")
    for txt_file in txt_files:
        os.chown(txt_file, user_id, group_id)
    
    print(f"✓ Logs saved to: {LOG_DIR}")

    # Stop all processes
    print("Stopping...")
    cleanup_processes()
    
    # Shutdown CORE session properly using API
    if session:
        session.set_state(EventTypes.DATACOLLECT_STATE)  # API: Set datacollect state
    
    if coreemu:
        coreemu.shutdown()  # API: Proper shutdown
    
    print("✓ Stopped")
    sys.exit(0)

def main():
    global XML_FILE, LOG_DIR, coreemu, session
    
    # Check if running with sudo
    if os.geteuid() != 0:
        print("Run with sudo")
        return 1
    
    # Setup Ctrl+C handler
    signal.signal(signal.SIGINT, stop)
    
    # Ask user which scenario to run
    print("\n" + "="*50)
    print("Which XML-Scenario do you want?")
    print("="*50)
    print("1. Static  - Static-Scenario (Mesh)")
    print("2. Dynamic - Dynamic-Scenario (Mobility)")
    print("="*50)
    
    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice == "1":
            XML_FILE = "/home/sina/.coregui/xmls/Static-Scenario (Mesh).xml"
            LOG_DIR = Path(__file__).parent / "logs_Static-Scenario_(Mesh)"
            scenario_name = "Static"
            break
        elif choice == "2":
            XML_FILE = "/home/sina/.coregui/xmls/Dynamic-Scenario (Mobility).xml"
            LOG_DIR = Path(__file__).parent / "logs_Dynamic-Scenario_(Mobility)"
            scenario_name = "Dynamic"
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")
    
    print(f"\n✓ Selected: {scenario_name} scenario\n")
    
    # Step 0: Cleanup old processes and files
    print("0. Cleanup...")
    cleanup_processes()
    print("   ✓ Stopped old processes")
    time.sleep(1)
    
    # Delete all bridge interfaces
    result = subprocess.run(
        "ip link show | grep -oP '[pb]\\.[0-9]+\\.[0-9]+(?=:)'",
        shell=True,
        capture_output=True,
        text=True
    )
    
    bridges = result.stdout.strip().split('\n')
    for bridge in bridges:
        if bridge:
            subprocess.run(["ip", "link", "delete", bridge], capture_output=True)
            print(f"   Deleted {bridge}")
    
    # Clean /tmp files
    subprocess.run(
        "rm -rf /tmp/pycore.* && rm -f /tmp/*.sock /tmp/rec_*.log",
        shell=True,
        capture_output=True
    )
    print("   ✓ Cleaned /tmp directories and files")
    
    # Extra cleanup using CORE's cleanup command
    subprocess.run(["core-cleanup"], capture_output=True)
    print("   ✓ CORE cleanup executed")
        
    # Step 1: Create CORE emulator and session using API
    print("1. Creating CORE session...")
    coreemu = CoreEmu()  # API: Create emulator instance
    session = coreemu.create_session()  # API: Create session programmatically
    print("   ✓ Session created")
    
    # Step 2: Load custom services using session.service_manager
    print("2. Loading custom services...")
    session.service_manager.load(Path("/home/sina/.coregui/custom_services"))  # API: Load services
    print("   ✓ Custom services loaded")
    
    # Step 3: Load XML scenario using session.open_xml() API
    print("3. Loading XML...")
    session.set_state(EventTypes.CONFIGURATION_STATE)  # API: Set session state
    session.open_xml(file_path=Path(XML_FILE), start=True)  # API: Load and start XML
    print("   ✓ XML loaded and services started")
    
    # Step 4: Wait for services to initialize
    print("4. Waiting for services to initialize...")
    time.sleep(15)
    
    print(f"   ✓ Found {len(session.nodes)} nodes")
    print("\n✓ Everything running! Press Ctrl+C to stop and collect logs.\n")
    
    # Wait forever
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop()

if __name__ == "__main__":
    sys.exit(main())
