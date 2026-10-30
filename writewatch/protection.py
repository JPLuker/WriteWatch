"""Conservative filesystem operations: never overwrite exports or follow links."""
import os
from pathlib import Path
import stat


def linked(path):
    path = Path(path)
    return path.is_symlink() or path.is_junction()


def safe_directory(path):
    """Reject redirected cleanup roots, including redirected ancestors.

    Resolve only the OS's standard macOS /var and /tmp aliases; user-created
    directory symlinks and Windows junctions are never cleanup destinations.
    """
    path = Path(path).absolute()
    for parent in (path, *path.parents):
        if linked(parent):
            if os.sys.platform == 'darwin' and str(parent) in ('/var', '/tmp'):
                continue
            return False
    return path.is_dir()


def matches(path, protected):
    for other in protected:
        other = Path(other)
        if path.absolute() == other.absolute():
            return True
        try:
            if path.resolve() == other.resolve() or path.samefile(other):
                return True
        except OSError:
            pass
    return False


def regular_unlinked(path):
    path = Path(path)
    try:
        info = path.lstat()
        return not linked(path) and stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    except FileNotFoundError:
        return False


def remove_file(path, protected=()):
    """Only remove a single regular file. Never recurse, follow or unlink links."""
    path = Path(path)
    if safe_directory(path.parent) and regular_unlinked(path) and not matches(path, protected):
        path.unlink()
        return True
    return False


def writable_app_file(path):
    """Refuse app files redirected into documents by symlinks or hard links."""
    path = Path(path)
    if not safe_directory(path.parent):
        raise ValueError('App storage must be a regular folder, not a linked folder.')
    if os.path.lexists(path) and not regular_unlinked(path):
        raise ValueError('An app data file is a link or folder. Choose a separate app data folder.')


def write_new(path, data):
    """Exclusive creation: existing files, hard links and symlinks are untouched.

    O_EXCL also refuses a destination that appears after the file picker closes.
    Failure removes only the new inode created by this call, if still present.
    """
    path = Path(path)
    with path.open('xb') as target:
        identity = os.fstat(target.fileno())
        try:
            target.write(data)
            target.flush()
            os.fsync(target.fileno())
        except BaseException:
            target.close()
            try:
                current = path.lstat()
                if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                    path.unlink()
            except OSError:
                pass
            raise
