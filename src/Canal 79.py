import subprocess
import psutil
from pathlib import Path
import vMixApiWrapper

def isVmixRunning():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'vMix64.exe':
            return True
        
    return False

if __name__ == "__main__":
    vMix = vMixApiWrapper()
    BASE_DIR = Path(__file__).resolve().parent
    schedulerPath = BASE_DIR / "scheduler.py"
    presetPath = BASE_DIR.parent() / "resources" / "vmix_resources" / "presetC79.vmix"

    if isVmixRunning():
        vMix.openPreset(presetPath)
        subprocess.run(["python",f"{schedulerPath}"])
