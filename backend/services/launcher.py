import subprocess
import os
import shutil

class Launcher:
    def launch(self, path: str, launch_type: str):
        # We are running ON Windows now.
        # path is already "D:\projects\..."
        
        if launch_type == "vscode":
            # "code" should be in the PATH on Windows
            subprocess.Popen(["code", path], shell=True)
            
        elif launch_type == "explorer":
            # Standard Windows launch (respects default file manager)
            os.startfile(path)
            
        elif launch_type == "terminal":
            # wt.exe -d "D:\projects\..."
            subprocess.Popen(["wt.exe", "-d", path], shell=True)

        elif launch_type == "wsl":
            # Manual conversion to WSL path
            drive, tail = os.path.splitdrive(path) 
            drive_letter = drive[0].lower()
            wsl_path = f"/mnt/{drive_letter}{tail.replace('\\', '/')}"
            
            print(f"Launching WSL Force-CD: {wsl_path}")
            
            # wt.exe -p "Ubuntu" -- wsl.exe -e bash -c "cd 'path' && exec bash"
            # We use 'exec bash' to keep the terminal open after cd.
            # Note: We default to default profile if -p is omitted, but adding -p "Ubuntu" 
            # helps if your default is PowerShell. 
            # Let's omit -p to use your default WSL profile if set, or just 'wsl.exe' handles it.
            
            cmd = f'wt.exe wsl.exe -e bash -c "cd \'{wsl_path}\' && exec bash"'
            subprocess.Popen(cmd, shell=True)
            
        else:
            raise ValueError(f"Unknown launch type: {launch_type}")
