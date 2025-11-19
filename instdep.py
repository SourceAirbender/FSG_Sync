"""
Module enabling you to install dependencies via pip.

"""

try:
    from importlib.metadata import version
    from packaging.version import parse
    import pip
    HAVE_PIP = True
except ImportError:
    HAVE_PIP = False

def instDep(module, min_version):
    """instDep tries to install the given dependency if needed."""
    if not HAVE_PIP:
        return
    try:
        current = version(module)
    except Exception:
        current = "0.0.0"
    if parse(current) < parse(min_version):
        print(f"Dependency {module} not found or < {min_version}")
        pip.main(['install', '--user', '--upgrade', '--break-system-packages', module])
        pip.main(['install', '--user', '--upgrade', '--break-system-packages', module, '--only-binary', ':all:'])

