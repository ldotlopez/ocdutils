import subprocess


class ProcessFailure(Exception):
    def __init__(self, *, args, rc, stdout, stderr):
        self.args = args
        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr


def run(*args: str, expected_rc: int | list[int] = 0):
    if isinstance(expected_rc, int):
        expected_rc = [expected_rc]
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    stdout, stderr = proc.communicate()
    if proc.returncode not in expected_rc:
        raise ProcessFailure(
            args=args, rc=proc.returncode, stdout=stdout, stderr=stderr
        )
