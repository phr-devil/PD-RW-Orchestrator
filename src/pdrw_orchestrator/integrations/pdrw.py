"""Discover installed PDRW package; do not misreport it as a live MCP connection."""
from importlib.util import find_spec


def pdrw_status() -> dict:
    installed = find_spec("pdrw_agent") is not None
    return {
        "component": "PD-RW-Agent",
        "python_package_importable": installed,
        "mcp_connected": False,
        "project_identity_authenticated": False,
        "host_permission_verified": False,
        "status": "ADAPTER_NOT_CONNECTED",
    }
