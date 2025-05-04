import subprocess
import time

server_process = subprocess.Popen(["python", "server.py"])

time.sleep(2)

launcher_process = subprocess.Popen(["python", "auth.py"])

launcher_process.wait()

server_process.terminate()
