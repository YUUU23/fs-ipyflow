import subprocess
import tempfile
import platform
import os
import time

"""
with open(fp) as f:
    ...
"""


"""
with STracer() as f: // Stracer.__enter__
                //  - Spawn a subprocess which straces the current process, and the current process' children excluding strace itself
                //  - Write all strace events to a tmp file
    ...
    trace_events = f.parse_trace_events()
    // Exit context ->
    // Stracer.__exit__
    //  - Delete tmp file
    //  - Remove strace sub process

do stuff with trace_events
"""

class STraceEvent():
    SYSCALLS = [
        "write",
        "read",
    ]

    def __init__(self):
        self.tmp_file = tempfile.NamedTemporaryFile(delete=False, mode="w+")

    def parse_fs_usage_events(self) -> str:
        save_syscall = None
        with open(self.tmp_file.name) as f:
            for line in f:
                # print("parsed line in fs: ", line)
                tokens = [token for token in line.split() if token]
                syscall = tokens[1]
                if syscall in self.SYSCALLS:
                    return syscall
        return save_syscall

    def check_syscall_occured(self) -> bool:
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
            self.call_fs_usage(cur_pid) # Use fs_usage on mac, watch for cur_pid (nb)
        elif platform.system() == "Linux":
            self.call_strace(cur_pid) # Use strace on Linux, watch for cur_pin (nb)
        else:
            raise OSError("Unsupported Platform!")
        time.sleep(0.5) # wait for spawn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        time.sleep(1)
        self.strace_events.tmp_file.flush() # flush tmp file
        if self.strace_process:
            # print(f"Cleaning process with pid {self.strace_process.pid}")
            if not self.strace_process.poll(): # not terminated 
                # print("Terminating")
                self.strace_process.terminate() # terminate

            time.sleep(0.5)
            if not self.strace_process.poll():
                # print("Killing")
                self.strace_process.kill() 