"""Windows AppContainer + Job Object launcher. No unrestricted fallback.

Only inherited anonymous pipes cross the boundary. Each invocation has a fresh
AppContainer profile, removed when its process is closed.
"""
import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import subprocess
import threading
import uuid


class SandboxUnavailable(RuntimeError):
    pass


class SID_AND_ATTRIBUTES(C.Structure):
    _fields_ = [("Sid", C.c_void_p), ("Attributes", W.DWORD)]


class SECURITY_CAPABILITIES(C.Structure):
    _fields_ = [("AppContainerSid", C.c_void_p), ("Capabilities", C.POINTER(SID_AND_ATTRIBUTES)),
                ("CapabilityCount", W.DWORD), ("Reserved", W.DWORD)]


class STARTUPINFO(C.Structure):
    _fields_ = [("cb", W.DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR),
        ("lpTitle", W.LPWSTR), ("dwX", W.DWORD), ("dwY", W.DWORD),
        ("dwXSize", W.DWORD), ("dwYSize", W.DWORD), ("dwXCountChars", W.DWORD),
        ("dwYCountChars", W.DWORD), ("dwFillAttribute", W.DWORD),
        ("dwFlags", W.DWORD), ("wShowWindow", W.WORD), ("cbReserved2", W.WORD),
        ("lpReserved2", C.c_void_p), ("hStdInput", W.HANDLE), ("hStdOutput", W.HANDLE),
        ("hStdError", W.HANDLE)]


class STARTUPINFOEX(C.Structure):
    _fields_ = [("StartupInfo", STARTUPINFO), ("lpAttributeList", C.c_void_p)]


class PROCESS_INFORMATION(C.Structure):
    _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE),
                ("dwProcessId", W.DWORD), ("dwThreadId", W.DWORD)]


class BASIC_LIMITS(C.Structure):
    _fields_ = [("PerProcessUserTimeLimit", C.c_longlong), ("PerJobUserTimeLimit", C.c_longlong),
        ("LimitFlags", W.DWORD), ("MinimumWorkingSetSize", C.c_size_t),
        ("MaximumWorkingSetSize", C.c_size_t), ("ActiveProcessLimit", W.DWORD),
        ("Affinity", C.c_size_t), ("PriorityClass", W.DWORD), ("SchedulingClass", W.DWORD)]


class IO_COUNTERS(C.Structure):
    _fields_ = [(name, C.c_ulonglong) for name in ("ReadOperationCount", "WriteOperationCount",
        "OtherOperationCount", "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class EXTENDED_LIMITS(C.Structure):
    _fields_ = [("BasicLimitInformation", BASIC_LIMITS), ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", C.c_size_t), ("JobMemoryLimit", C.c_size_t),
        ("PeakProcessMemoryUsed", C.c_size_t), ("PeakJobMemoryUsed", C.c_size_t)]


def _apis():
    if os.name != "nt":
        raise SandboxUnavailable("sandbox_windows_required")
    k = C.WinDLL("kernel32", use_last_error=True)
    u = C.WinDLL("userenv", use_last_error=True)
    a = C.WinDLL("advapi32", use_last_error=True)
    declarations = [
        (k, "CreateJobObjectW", [C.c_void_p, W.LPCWSTR], W.HANDLE),
        (k, "SetInformationJobObject", [W.HANDLE, C.c_int, C.c_void_p, W.DWORD], W.BOOL),
        (k, "AssignProcessToJobObject", [W.HANDLE, W.HANDLE], W.BOOL),
        (k, "TerminateJobObject", [W.HANDLE, W.UINT], W.BOOL),
        (k, "TerminateProcess", [W.HANDLE, W.UINT], W.BOOL),
        (k, "CloseHandle", [W.HANDLE], W.BOOL),
        (k, "InitializeProcThreadAttributeList", [C.c_void_p, W.DWORD, W.DWORD, C.POINTER(C.c_size_t)], W.BOOL),
        (k, "UpdateProcThreadAttribute", [C.c_void_p, W.DWORD, C.c_size_t, C.c_void_p, C.c_size_t, C.c_void_p, C.c_void_p], W.BOOL),
        (k, "DeleteProcThreadAttributeList", [C.c_void_p], None),
        (k, "CreateProcessW", [W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, W.DWORD,
            C.c_void_p, W.LPCWSTR, C.POINTER(STARTUPINFOEX), C.POINTER(PROCESS_INFORMATION)], W.BOOL),
        (k, "ResumeThread", [W.HANDLE], W.DWORD),
        (k, "WaitForSingleObject", [W.HANDLE, W.DWORD], W.DWORD),
        (k, "GetExitCodeProcess", [W.HANDLE, C.POINTER(W.DWORD)], W.BOOL),
        (k, "LocalFree", [C.c_void_p], C.c_void_p),
        (u, "DeriveAppContainerSidFromAppContainerName", [W.LPCWSTR, C.POINTER(C.c_void_p)], C.c_long),
        (u, "CreateAppContainerProfile", [W.LPCWSTR, W.LPCWSTR, W.LPCWSTR, C.c_void_p, W.DWORD, C.POINTER(C.c_void_p)], C.c_long),
        (u, "DeleteAppContainerProfile", [W.LPCWSTR], C.c_long),
        (a, "ConvertStringSidToSidW", [W.LPCWSTR, C.POINTER(C.c_void_p)], W.BOOL),
        (a, "FreeSid", [C.c_void_p], C.c_void_p),
    ]
    for dll, name, args, result in declarations:
        function = getattr(dll, name); function.argtypes = args; function.restype = result
    return k, u, a


def _check(value):
    if not value:
        raise SandboxUnavailable("sandbox_win32_error_" + str(C.get_last_error()))
    return value


class SandboxedProcess:
    def __init__(self, kernel, handle, job, pid, stdin, stdout, stderr, userenv, profile):
        self._kernel, self._handle, self._job = kernel, handle, job
        self.pid, self.stdin, self.stdout, self.stderr = pid, stdin, stdout, stderr
        self.returncode = None
        self._userenv, self._profile = userenv, profile

    def poll(self):
        if self.returncode is None:
            result = self._kernel.WaitForSingleObject(self._handle, 0)
            if result == 0:
                code = W.DWORD(); _check(self._kernel.GetExitCodeProcess(self._handle, C.byref(code)))
                self.returncode = code.value
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            result = self._kernel.WaitForSingleObject(self._handle, 0xffffffff if timeout is None else max(0, int(timeout * 1000)))
            if result == 258:
                raise subprocess.TimeoutExpired("sandbox_worker", timeout)
            if result != 0:
                raise SandboxUnavailable("sandbox_wait_failed")
        return self.poll()

    def kill(self):
        if self._job:
            _check(self._kernel.TerminateJobObject(self._job, 137))

    def communicate(self, input=None, timeout=None, maximum=1024 * 1024):
        # Bounded concurrent pipe draining. Overflow kills the entire job.
        output, errors = bytearray(), []
        def read():
            try:
                while chunk := self.stdout.read(16384):
                    if len(output) + len(chunk) > maximum:
                        errors.append("sandbox_output_limit"); self.kill(); break
                    output.extend(chunk)
            except OSError:
                errors.append("sandbox_pipe_failed")
        def write():
            try:
                if input: self.stdin.write(input)
                self.stdin.close()
            except (OSError, ValueError):
                pass
        reader = threading.Thread(target=read, daemon=True)
        writer = threading.Thread(target=write, daemon=True)
        reader.start(); writer.start()
        try:
            self.wait(timeout)
        except subprocess.TimeoutExpired:
            self.kill(); self.wait(3)
            reader.join(3); writer.join(3)
            raise
        reader.join(3); writer.join(3)
        if reader.is_alive() or writer.is_alive():
            self.kill()
            raise SandboxUnavailable("sandbox_pipe_timeout")
        if errors:
            raise SandboxUnavailable(errors[0])
        return bytes(output), None

    def close(self):
        if self._handle and self.poll() is None:
            self.kill(); self.wait(3)
        if self._job:
            # KILL_ON_JOB_CLOSE also handles an unexpectedly surviving descendant.
            self._kernel.CloseHandle(self._job); self._job = None
        if self._handle:
            self._kernel.CloseHandle(self._handle); self._handle = None
        for stream in (self.stdin, self.stdout, self.stderr):
            if stream and not stream.closed:
                try: stream.close()
                except OSError: pass  # A killed child may have broken its stdin pipe.
        if self._profile:
            result = self._userenv.DeleteAppContainerProfile(self._profile)
            self._profile = None
            if result != 0:
                raise SandboxUnavailable("sandbox_profile_cleanup_failed")


def launch(root: Path, module: str, *, internet=False, memory_mb=256, cpu_seconds=10):
    """Trusted internal launcher; callers choose a fixed module, never user code."""
    k, u, a = _apis()
    import msvcrt
    root = root.resolve(strict=True)
    executable = root / "python.exe"
    sid, capability = C.c_void_p(), C.c_void_p()
    job, attributes, process, pipes = None, None, PROCESS_INFORMATION(), []
    transferred, initialized, profile_created = False, False, False
    profile = "Operia.Ephemeral." + uuid.uuid4().hex
    try:
        if u.CreateAppContainerProfile(profile, profile, "Disposable OPERIA worker", None, 0, C.byref(sid)) != 0:
            raise SandboxUnavailable("sandbox_identity_failed")
        profile_created = True
        capabilities = None
        if internet:
            _check(a.ConvertStringSidToSidW("S-1-15-3-1", C.byref(capability)))  # internetClient only
            capabilities = (SID_AND_ATTRIBUTES * 1)(SID_AND_ATTRIBUTES(capability, 4))
        security = SECURITY_CAPABILITIES(sid, capabilities, int(internet), 0)
        job = _check(k.CreateJobObjectW(None, None))
        limits = EXTENDED_LIMITS()
        limits.BasicLimitInformation.LimitFlags = 0x2000 | 0x8 | 0x100 | 0x2  # kill-on-close, active, memory, CPU
        limits.BasicLimitInformation.ActiveProcessLimit = 1
        limits.BasicLimitInformation.PerProcessUserTimeLimit = cpu_seconds * 10_000_000
        limits.ProcessMemoryLimit = memory_mb * 1024 * 1024
        _check(k.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)))
        ui_restrictions = W.DWORD(0xff)  # Clipboard, desktop, USER handles, atoms, display, shutdown.
        _check(k.SetInformationJobObject(job, 4, C.byref(ui_restrictions), C.sizeof(ui_restrictions)))
        # os.pipe handles default to non-inheritable. Whitelist only the child ends.
        input_read, input_write = os.pipe(); pipes.extend([input_read, input_write])
        output_read, output_write = os.pipe(); pipes.extend([output_read, output_write])
        null = os.open(os.devnull, os.O_WRONLY); pipes.append(null)
        child_fds = (input_read, output_write, null)
        for fd in child_fds: os.set_inheritable(fd, True)
        handles = (W.HANDLE * 3)(*(msvcrt.get_osfhandle(fd) for fd in child_fds))
        size = C.c_size_t()
        k.InitializeProcThreadAttributeList(None, 2, 0, C.byref(size))
        attributes = C.create_string_buffer(size.value)
        _check(k.InitializeProcThreadAttributeList(attributes, 2, 0, C.byref(size)))
        initialized = True
        _check(k.UpdateProcThreadAttribute(attributes, 0, 0x20002, handles, C.sizeof(handles), None, None))
        _check(k.UpdateProcThreadAttribute(attributes, 0, 0x20009, C.byref(security), C.sizeof(security), None, None))
        startup = STARTUPINFOEX(); startup.StartupInfo.cb = C.sizeof(startup)
        startup.StartupInfo.dwFlags = 0x100
        startup.StartupInfo.hStdInput, startup.StartupInfo.hStdOutput, startup.StartupInfo.hStdError = handles
        startup.lpAttributeList = C.cast(attributes, C.c_void_p)
        command = C.create_unicode_buffer(subprocess.list2cmdline([str(executable), "-I", "-S", "-B", "-m", module]))
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        # Windows resolves package storage while creating the token. Only OS
        # location metadata is inherited; no application secrets or proxies.
        env = {key: os.environ[key] for key in ("USERPROFILE", "LOCALAPPDATA", "APPDATA") if key in os.environ}
        env.update(SystemRoot=system_root, WINDIR=system_root)
        environment = C.create_unicode_buffer("\0".join(key + "=" + value for key, value in sorted(env.items())) + "\0\0")
        _check(k.CreateProcessW(str(executable), command, None, None, True,
            0x80000 | 0x4 | 0x400 | 0x08000000, environment, str(root), C.byref(startup), C.byref(process)))
        # No Python instruction runs before the kernel has applied the job limits.
        _check(k.AssignProcessToJobObject(job, process.hProcess))
        if k.ResumeThread(process.hThread) == 0xffffffff:
            raise SandboxUnavailable("sandbox_resume_failed")
        for fd in child_fds: os.close(fd); pipes.remove(fd)
        child = SandboxedProcess(k, process.hProcess, job, process.dwProcessId,
            os.fdopen(input_write, "wb"), os.fdopen(output_read, "rb", buffering=0), None, u, profile)
        pipes.remove(input_write); pipes.remove(output_read)
        transferred = True
        return child
    finally:
        if process.hThread: k.CloseHandle(process.hThread)
        if not transferred:
            if job: k.TerminateJobObject(job, 137)
            if process.hProcess:
                k.TerminateProcess(process.hProcess, 137); k.WaitForSingleObject(process.hProcess, 3000)
            if process.hProcess: k.CloseHandle(process.hProcess)
            if job: k.CloseHandle(job)
            if profile_created: u.DeleteAppContainerProfile(profile)
        for fd in pipes: os.close(fd)
        if initialized: k.DeleteProcThreadAttributeList(attributes)
        if capability: k.LocalFree(capability)
        if sid: a.FreeSid(sid)
