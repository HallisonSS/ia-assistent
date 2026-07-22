import platform
import shutil


def get_system_info():

    disk = shutil.disk_usage("/")

    return {
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "disk_total_gb":
            round(
                disk.total / 1024**3,
                2
            ),
        "disk_free_gb":
            round(
                disk.free / 1024**3,
                2
            ),
    }
