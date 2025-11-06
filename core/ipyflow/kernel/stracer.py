import subprocess
import tempfile
import platform
import os
import time
from collections import defaultdict

class STraceEvent():
    FS_SYSCALLS = [
        "write",
        "read",
        "open", 
    ]

    def __init__(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="w+")

    def parse_fs_usage_events(self) -> list[str, str]:
        opened_fd_to_fname = defaultdict(str)
        with open(self.tmp_file.name) as f:
            for line in f:
                tokens = [token for token in line.split() if token]
                syscall = tokens[1]
                if syscall in self.FS_SYSCALLS:
                    fd = int(tokens[2].split("=")[1])
                    if syscall == "open":
                        fname = tokens[4]
                        opened_fd_to_fname[fd] = fname
                    elif syscall == "read": 
                        if fd not in opened_fd_to_fname: 
                            raise ValueError("fd not found; read case")
                        fname = opened_fd_to_fname[fd]
                        print("== [backend print] !!! FNAME FOUND READ: ", fname)
                        return (syscall, fname)
                    elif syscall == "write": 
                        if fd not in opened_fd_to_fname: 
                            raise ValueError("fd not found; write case")
                        fname = opened_fd_to_fname[fd]
                        print("== [backend print] !!! FNAME FOUND WRITE: ", fname)
                        return (syscall, fname)
        
        return ("", "")

    def check_syscall_occurred(self) -> bool:
        if platform.system() == "Darwin":
            return self.parse_fs_usage_events()
        elif platform.system() == "Linux":
            return self.parse_strace_events()
        else:
            raise OSError("Unsupported Platform!")

class STracer():
    def __init__(self, events: STraceEvent, strace_path = "/bin/strace", fs_usage_path = "/usr/bin/fs_usage"):
        self.strace_events = events
        self.strace_path = strace_path
        self.fs_usage_path = fs_usage_path
        self.strace_process = None
    
    def call_strace(self, pid: int | str) -> None:
        strace_args = [
            self.strace_path,
            "-y",             # Translate file descriptors to paths
            "-f",             # Follow forks of the target process
            "-p",             # Attach onto a running process (cur_pid)
            str(pid),
            "-o",             # Output to given file (tmp file)
            self.strace_events.tmp_file.name,
        ]
        self.strace_process = subprocess.Popen(strace_args, stdout = subprocess.DEVNULL)

    def call_fs_usage(self, pid: int | str) -> None:
        fs_usage_args = [
            "sudo",
            self.fs_usage_path,
            "-w",
            str(pid)
        ]
        self.strace_process = subprocess.Popen(fs_usage_args, stdout=self.strace_events.tmp_file)

    def __enter__(self):
        cur_pid = os.getpid()

        if platform.system() == "Darwin":
            # Use fs_usage on mac, watch for cur_pid (nb)
            self.call_fs_usage(cur_pid) 
        elif platform.system() == "Linux":
            # Use strace on Linux, watch for cur_pin (nb)
            self.call_strace(cur_pid) 
        else:
            raise OSError("Unsupported Platform!")
        time.sleep(0.5) # wait for spawn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        time.sleep(1)
        self.strace_events.tmp_file.flush() # flush tmp file
        if self.strace_process:
            if not self.strace_process.poll(): # not terminated 
                self.strace_process.terminate() # terminate

            time.sleep(0.5)
            if not self.strace_process.poll():
                self.strace_process.kill() # kill if still not terminated