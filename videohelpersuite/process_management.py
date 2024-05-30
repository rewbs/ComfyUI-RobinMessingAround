import time
import random
import os
import subprocess
import threading


class ProcessManager:

    def __init__(self, logger):
        self.logger = logger

    ##
    # Forward lines from source to logger.
    ##
    def forward_to_log(self, src, log_prefix):
        for line in src:
            self.logger.info(f"[{log_prefix}] - {line.rstrip()}")

    ##
    # Run a command and return its subprocess. Forward its output to stdout/stderr if print_output is True.
    ##
    def run_process(self, cmd, cwd = None, env = None, print_output=True, log_prefix='', shell=False):
        # Prepare the environment variables
        final_env = os.environ.copy()  # Start with existing environment variables
        if env:
            final_env.update(env)  # Update with custom variables
        proc = subprocess.Popen(
            cmd,
            cwd=cwd, 
            env=final_env,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This ensures that stdout and stderr are strings, not bytes
            bufsize=1  # Line buffered
        )    
        if print_output:
            stdOutThread = threading.Thread(target=self.forward_to_log, args=(proc.stdout, log_prefix))
            stdOutThread.setName(f"stdout-{log_prefix}")
            stdOutThread.setDaemon(True)
            stdOutThread.start()
            stdErrThread = threading.Thread(target=self.forward_to_log, args=(proc.stderr, log_prefix))
            stdErrThread.setName(f"stderr-{log_prefix}")
            stdErrThread.setDaemon(True)
            stdErrThread.start()

        return proc


    ##
    # As long as process `main_proc` is alive, run shell command `cmd` every `interval` seconds,
    # prefixing all stdout/stderr output with `log_prefix` and a timestamp.
    ##
    def monitor_and_run_cmd_repeatedly(self, main_proc : subprocess.Popen[str], cmd, cwd=None, env=None, log_prefix='', interval=10, shell=False):
        """Run a command every interval until the main process completes."""
        time.sleep(int(random.random()*interval))
        try:
            self.logger.info(f"[{log_prefix}] Starting monitor tracking main process {main_proc.pid}")
            while main_proc.poll() is None:  # Check if the main process is still running
                sub_proc = self.run_process(cmd, cwd=cwd, env=env, log_prefix=log_prefix, shell=shell)
                sub_proc.wait()
                for i in range(interval):
                    # Every second for interval seconds, check to see if the main process is still running
                    if main_proc.poll() is not None:
                        raise InterruptedError
                    time.sleep(1)
        except InterruptedError:
            pass

        self.logger.info(f"[{log_prefix}] Monitor ending. Main process {main_proc.pid} terminated with exit code {main_proc.returncode}.")