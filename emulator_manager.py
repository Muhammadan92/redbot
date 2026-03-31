"""Manage Android emulator and Appium server lifecycle."""

import os
import re
import signal
import subprocess
import time

ANDROID_HOME = os.getenv("ANDROID_HOME", os.path.expanduser("~/Library/Android/sdk"))
DEFAULT_AVD = os.getenv("ANDROID_AVD_NAME", "redbot_pixel7")
DEFAULT_PORT = int(os.getenv("EMULATOR_PORT", "5554"))
APPIUM_PORT = int(os.getenv("APPIUM_PORT", "4723"))

_appium_proc = None


def _adb(*args):
    """Run an adb command and return stdout."""
    adb_path = os.path.join(ANDROID_HOME, "platform-tools", "adb")
    if not os.path.exists(adb_path):
        adb_path = "adb"  # Fall back to PATH
    result = subprocess.run(
        [adb_path, *args],
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def is_emulator_running(serial=None):
    """Check if an emulator is running and ready."""
    serial = serial or f"emulator-{DEFAULT_PORT}"
    output = _adb("devices")
    for line in output.splitlines():
        if serial in line and "device" in line and "offline" not in line:
            return True
    return False


def start_emulator(avd_name=None, port=None, headless=True):
    """Start the Android emulator and wait for it to boot.

    Returns the device serial (e.g. 'emulator-5554').
    """
    avd_name = avd_name or DEFAULT_AVD
    port = port or DEFAULT_PORT
    serial = f"emulator-{port}"

    if is_emulator_running(serial):
        return serial

    emulator_path = os.path.join(ANDROID_HOME, "emulator", "emulator")
    if not os.path.exists(emulator_path):
        emulator_path = "emulator"

    cmd = [
        emulator_path,
        "-avd", avd_name,
        "-port", str(port),
        "-no-audio",
        "-gpu", "swiftshader_indirect",
    ]
    if headless:
        cmd.append("-no-window")

    subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    wait_for_boot(serial)
    return serial


def wait_for_boot(serial=None, timeout=120):
    """Wait for the emulator to finish booting."""
    serial = serial or f"emulator-{DEFAULT_PORT}"
    deadline = time.time() + timeout

    # First wait for the device to appear in adb
    while time.time() < deadline:
        if is_emulator_running(serial):
            break
        time.sleep(2)
    else:
        raise RuntimeError(f"Emulator {serial} did not appear within {timeout}s")

    # Then wait for boot_completed property
    while time.time() < deadline:
        try:
            output = _adb("-s", serial, "shell", "getprop", "sys.boot_completed")
            if output.strip() == "1":
                return
        except subprocess.TimeoutExpired:
            pass
        time.sleep(3)

    raise RuntimeError(f"Emulator {serial} did not finish booting within {timeout}s")


def stop_emulator(serial=None):
    """Stop the emulator."""
    serial = serial or f"emulator-{DEFAULT_PORT}"
    try:
        _adb("-s", serial, "emu", "kill")
    except Exception:
        pass


def start_appium(port=None):
    """Start the Appium server if it's not already running."""
    global _appium_proc
    port = port or APPIUM_PORT

    if is_appium_running(port):
        return

    _appium_proc = subprocess.Popen(
        ["appium", "--port", str(port), "--log-level", "error"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for Appium to be ready
    deadline = time.time() + 30
    while time.time() < deadline:
        if is_appium_running(port):
            return
        time.sleep(1)

    raise RuntimeError(f"Appium server did not start on port {port} within 30s")


def is_appium_running(port=None):
    """Check if Appium is listening on the given port."""
    port = port or APPIUM_PORT
    try:
        import urllib.request
        urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=3)
        return True
    except Exception:
        return False


def stop_appium():
    """Stop the Appium server if we started it."""
    global _appium_proc
    if _appium_proc is not None:
        try:
            _appium_proc.send_signal(signal.SIGTERM)
            _appium_proc.wait(timeout=10)
        except Exception:
            _appium_proc.kill()
        _appium_proc = None
