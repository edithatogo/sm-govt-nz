import os
import subprocess
import sys


def check_ssh_access(host: str) -> bool:
    print(f"Checking SSH access to {host}...")
    try:
        # We try to connect to SSH. -o BatchMode=yes prevents interactive prompts.
        result = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", f"git@{host}"],
            capture_output=True,
            text=True,
            check=False,
        )
        # Most git hosts return an error code but a welcome message on success.
        # e.g. "Hi <user>! You've successfully authenticated..."
        if "successfully authenticated" in result.stderr or "successfully authenticated" in result.stdout:
            return True
        if "Connection refused" in result.stderr or "timed out" in result.stderr:
            return False
        # If we get a "Permission denied (publickey)", it means the key is missing or wrong.
        return False
    except OSError as error:
        print(f"Error checking SSH: {error}")
        return False


def validate_mirrors():
    mirror_url = os.getenv("GIT_MIRROR_URL")
    if not mirror_url:
        print("GIT_MIRROR_URL environment variable is not set.")
        return False

    # Extract host from git@host:user/repo.git or https://host/user/repo.git
    if "@" in mirror_url:
        host = mirror_url.split("@")[1].split(":")[0]
        if check_ssh_access(host):
            print(f"Successfully validated SSH access to {host}")
            return True
        print(f"Failed to validate SSH access to {host}")
        return False
    else:
        print("HTTPS mirrors are not validated by this script (requires token check).")
        return True


if __name__ == "__main__":
    if not validate_mirrors():
        sys.exit(1)
