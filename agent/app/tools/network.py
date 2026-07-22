import subprocess


def network_status():

    result = subprocess.run(
        [
            "ip",
            "-br",
            "addr"
        ],
        capture_output=True,
        text=True,
        timeout=10
    )

    return result.stdout
