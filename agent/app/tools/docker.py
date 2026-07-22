import subprocess


def docker_ps():

    result = subprocess.run(
        [
            "docker",
            "ps",
            "--format",
            "{{.Names}} | {{.Status}}"
        ],
        capture_output=True,
        text=True,
        timeout=10
    )

    return result.stdout
