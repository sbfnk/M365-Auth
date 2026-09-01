"""Small helpers shared by the token scripts."""
import os
import tempfile


def write_atomic(path, text):
    """Replace path's contents in one step.

    Opening for write truncates before any bytes land, so a process killed
    mid-write leaves an empty file that still passes an existence check. The
    next run would then read a blank refresh token and need interactive
    re-authentication.
    """
    path = str(path)
    directory = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=directory)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
