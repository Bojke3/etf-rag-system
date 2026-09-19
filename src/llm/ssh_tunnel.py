"""A short-lived OpenSSH tunnel to an existing remote Ollama service."""

import json
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen


def list_models(base_url, timeout=5):
    """Fetch model names and digests, failing visibly if Ollama is unavailable."""
    with urlopen(base_url.rstrip('/') + '/api/tags', timeout=timeout) as response:
        data = json.load(response)
    models = data.get('models')
    if not isinstance(models, list):
        raise ValueError('Ollama /api/tags did not return a model list.')
    return models


class SSHTunnel:
    """Use SSH keys/agent/config or OpenSSH's own interactive password prompt.

    Passwords are never read by Python or written to configuration/results.
    Host verification follows the user's OpenSSH configuration.
    """

    def __init__(self, host, user='', port=22, identity_file='', local_port=11435,
                 remote_host='127.0.0.1', remote_port=11434, startup_timeout=120):
        for value in (host, remote_host):
            if not value or value.startswith('-') or not re.fullmatch(r'[\w.:-]+', value):
                raise ValueError('Invalid SSH host or remote Ollama address.')
        if user and (user.startswith('-') or not re.fullmatch(r'[\w.-]+', user)):
            raise ValueError('Invalid SSH username.')
        if any(not 1 <= int(p) <= 65535 for p in (port, local_port, remote_port)):
            raise ValueError('Ports must be between 1 and 65535.')
        if startup_timeout <= 0:
            raise ValueError('SSH startup timeout must be positive.')
        self.host, self.user, self.port = host, user, port
        self.identity_file = identity_file
        self.local_port, self.remote_host, self.remote_port = local_port, remote_host, remote_port
        self.startup_timeout = startup_timeout
        self.process = None
        self.base_url = f'http://127.0.0.1:{local_port}'

    def command(self):
        executable = shutil.which('ssh')
        if not executable:
            raise RuntimeError('OpenSSH was not found. Install or enable OpenSSH Client.')
        remote = f'[{self.remote_host}]' if ':' in self.remote_host else self.remote_host
        command = [executable, '-N', '-T', '-o', 'ExitOnForwardFailure=yes',
                   '-o', 'ConnectTimeout=15', '-o', 'ServerAliveInterval=30',
                   '-o', 'ServerAliveCountMax=3', '-p', str(self.port),
                   '-L', f'127.0.0.1:{self.local_port}:{remote}:{self.remote_port}']
        if not sys.stdin.isatty():
            command.extend(['-o', 'BatchMode=yes'])
        if self.user:
            command.extend(['-l', self.user])
        if self.identity_file:
            key = Path(self.identity_file).expanduser()
            if not key.is_file():
                raise ValueError(f'SSH identity file does not exist: {key}')
            command.extend(['-i', str(key)])
        command.append(self.host)
        return command

    def __enter__(self):
        # Refuse to accidentally send requests to a pre-existing local listener.
        with socket.socket() as probe:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                # Windows: SO_REUSEADDR would let us bind over a live listener,
                # which is the one thing this probe exists to prevent.
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                # POSIX: without this, bind() also fails on the TIME_WAIT sockets
                # left by the previous run's HTTP requests -- no process holds the
                # port, yet the next run refuses to start for up to 2*MSL (30 s on
                # macOS). That failed six runs of the step-1 matrix. SO_REUSEADDR
                # clears TIME_WAIT only; a live listener still fails here, as ssh
                # itself sets the same option for the forwarded port.
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(('127.0.0.1', self.local_port))
            except OSError as exc:
                raise RuntimeError(f'Local port {self.local_port} is already in use; change SSH_LOCAL_PORT.') from exc
        try:
            print(f'Connecting to {self.host}; OpenSSH may prompt for host verification or a password.', flush=True)
            # No shell, detached windows, passwords in arguments, or remote commands.
            self.process = subprocess.Popen(self.command())
            deadline = time.monotonic() + self.startup_timeout
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RuntimeError('SSH connection failed. Check the OpenSSH message above.')
                try:
                    list_models(self.base_url, timeout=1)
                    if self.process.poll() is not None:
                        raise RuntimeError('The SSH tunnel disconnected during startup.')
                    return self
                except (OSError, ValueError):
                    time.sleep(0.2)
            raise RuntimeError('SSH/Ollama startup timed out. Check authentication and the remote Ollama port.')
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            self.process = None

    def __exit__(self, *exc):
        self.close()
