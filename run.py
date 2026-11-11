import os
import sys
import subprocess
import threading
import time
import webbrowser
import shutil
import signal

# Constants
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

def get_python_executable():
    venv_python = os.path.join(BACKEND_DIR, ".venv", "Scripts" if os.name == 'nt' else "bin", "python.exe" if os.name == 'nt' else "python")
    if os.path.exists(venv_python):
        return venv_python
    local_py311 = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Python\Python311\python.exe")
    if os.name == 'nt' and os.path.exists(local_py311):
        return local_py311
    return sys.executable

def check_prerequisites():
    print("Checking prerequisites...")
    py_exec = get_python_executable()
    # Check if we are running under an older python but have a valid 3.11 venv
    if sys.version_info < (3, 11) and py_exec == sys.executable:
        print("Error: Python 3.11+ is required.")
        sys.exit(1)
    
    if not shutil.which("node"):
        print("Error: Node.js is not installed or not in PATH.")
        sys.exit(1)
        
    if not shutil.which("npm"):
        print("Error: npm is not installed or not in PATH.")
        sys.exit(1)
    print("Prerequisites satisfied.")

def setup_env():
    env_path = os.path.join(BACKEND_DIR, ".env")
    env_example = os.path.join(BACKEND_DIR, ".env.example")
    
    if not os.path.exists(env_path):
        if os.path.exists(env_example):
            print("Copying backend/.env.example to backend/.env...")
            shutil.copyfile(env_example, env_path)
        else:
            print("Warning: backend/.env.example not found, could not create .env")
    else:
        print("backend/.env already exists.")

def stream_output(pipe, prefix):
    for line in iter(pipe.readline, b''):
        try:
            line_str = line.decode("utf-8").rstrip()
        except UnicodeDecodeError:
            line_str = line.decode("latin-1").rstrip()
        print(f"{prefix} {line_str}", flush=True)

def main():
    check_prerequisites()
    setup_env()

    print("Starting FastAPI Backend...")
    py_exec = get_python_executable()
    backend_cmd = [py_exec, "-m", "uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=BACKEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    print("Starting Vite React Frontend...")
    frontend_cmd = ["npm", "run", "dev"] if os.name != 'nt' else ["npm.cmd", "run", "dev"]
    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd=FRONTEND_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    backend_thread = threading.Thread(target=stream_output, args=(backend_process.stdout, "\033[94m[Backend]\033[0m"))
    backend_thread.daemon = True
    backend_thread.start()

    frontend_thread = threading.Thread(target=stream_output, args=(frontend_process.stdout, "\033[92m[Frontend]\033[0m"))
    frontend_thread.daemon = True
    frontend_thread.start()

    print("Waiting 2 seconds for services to initialize...")
    time.sleep(2)
    
    print("Opening browser to http://localhost:5173 ...")
    webbrowser.open("http://localhost:5173")

    def signal_handler(sig, frame):
        print("\nKeyboardInterrupt received, shutting down gracefully...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("All processes terminated. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
