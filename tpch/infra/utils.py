import socket
from datetime import date, datetime


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


def ping(host, port = 22, timeout = 1):
    "try to connect to a TCP port"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)

    # Try to Connect
    try:
        s.connect((host, int(port)))
        s.shutdown(socket.SHUT_RD)
        return True

    # Connection Timed Out
    except socket.timeout:
        return False

    except OSError as e:
        # Connection refuses is an OS Error and kind of expected here
        return False

    return True


def wait_for_service(host, port = 22, timeout = 1):
    "Ping given PORT on HOST until we could actually connect there."
    pong = ping(host, port, timeout)

    while pong is False:
        pong = ping(host, port, timeout)

    return True
