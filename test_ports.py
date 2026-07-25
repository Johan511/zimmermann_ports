#!/usr/bin/env python3
"""Build all zimmermann ports using cmake and zimmermann.

Usage: build_ports.py <zimmermann-install-path> [--no-clean] [--perf] [--port name1,name2]
"""

import os
import shutil
import subprocess
import sys
import time


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTS_DIR = os.path.join(SCRIPT_DIR, "ports")

PORTS = [
    {
        "name": "googletest",
        "binary": None,
        "expected": [],
        "artifacts": [
            "gtest.a", "gtest_main.a", "gmock.a", "gmock_main.a",
        ],
    },
]


def cmake_configure(port_dir: str, build_dir: str) -> bool:
    cmd = [
        "cmake",
        "-S", port_dir,
        "-B", build_dir,
    ]
    log_path = os.path.join(build_dir, "cmake_configure.log")
    with open(log_path, "w") as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    return result.returncode == 0


def cmake_build(build_dir: str) -> bool:
    cmd = [
        "cmake",
        "--build", build_dir
    ]
    log_path = os.path.join(build_dir, "cmake_build.log")
    with open(log_path, "w") as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    return result.returncode == 0


def build_ze_build(port_dir: str, build_dir: str, zimm_install: str) -> bool:
    source = os.path.join(port_dir, "ze_build.cpp")
    ze_bin = os.path.join(build_dir, "build_zimm")
    os.makedirs(os.path.dirname(ze_bin), exist_ok=True)

    includes = os.path.join(zimm_install, "include")
    lib_dir = os.path.join(zimm_install, "lib64")

    cmd = [
        "g++", source,
        "-std=c++23",
        "-I" + includes,
        "-o", ze_bin,
        "-L" + lib_dir, "-lzimmermann",
        "-Wall", "-Wextra", "-Wpedantic", "-Werror",
    ]
    result = subprocess.run(cmd, cwd=port_dir)
    return result.returncode == 0


def run_ze_build(build_dir: str) -> bool:
    ze_bin = os.path.join(build_dir, "build_zimm")
    if not os.path.isfile(ze_bin):
        return False
    log_path = os.path.join(build_dir, "zimm.log")
    with open(log_path, "w") as log:
        result = subprocess.run([ze_bin], stdout=log, stderr=subprocess.STDOUT, cwd=build_dir)
    return result.returncode == 0


def run_ninja(build_dir: str) -> bool:
    log_path = os.path.join(build_dir, "build.log")
    with open(log_path, "w") as log:
        result = subprocess.run(
            ["ninja", "-C", build_dir],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    return result.returncode == 0


def verify_artifacts(build_dir: str, artifacts: list[str]) -> bool:
    for path in artifacts:
        full = os.path.join(build_dir, path)
        if not os.path.exists(full):
            print(f"  missing artifact: {path}", file=sys.stderr)
            return False
    return True


def run_binary(build_dir: str, binary: str) -> str | None:
    bin_path = os.path.join(build_dir, binary)
    if not os.path.isfile(bin_path):
        print(f"  binary not found: {bin_path}", file=sys.stderr)
        return None
    result = subprocess.run([bin_path], capture_output=True, text=True, cwd=build_dir)
    return result.stdout if result.returncode == 0 else None


def check_output(stdout: str, expected: list[str]) -> bool:
    rest = stdout
    for line in expected:
        idx = rest.find(line)
        if idx == -1:
            print(f"  expected substring not found in output: {line!r}", file=sys.stderr)
            print(f"  stdout was: {stdout[:200]}", file=sys.stderr)
            return False
        rest = rest[idx + len(line):]
    return True


def build_port_cmake(port: dict, no_clean: bool = False, perf: bool = False) -> bool:
    name = port["name"]
    port_dir = os.path.join(PORTS_DIR, name)
    build_dir = os.path.join(port_dir, "build_cmake")

    banner = f"cmake {name}"
    if not no_clean:
        shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)

    t0 = time.perf_counter()
    if not cmake_configure(port_dir, build_dir):
        print(f"FAIL  {banner}: configure")
        return False
    t1 = time.perf_counter()

    if not cmake_build(build_dir):
        print(f"FAIL  {banner}: build")
        return False
    t2 = time.perf_counter()

    if perf:
        print(
            f"PASS  {banner}\n"
            f"  cmake_configure: {(t1 - t0) * 1000:.1f}ms\n"
            f"  cmake_build:     {(t2 - t1) * 1000:.1f}ms"
        )
    else:
        print(f"PASS  {banner}")
    return True


def build_port_zimmermann(port: dict, zimm_install: str, no_clean: bool = False, perf: bool = False) -> bool:
    name = port["name"]
    binary = port.get("binary")
    expected = port.get("expected", [])
    artifacts = port.get("artifacts", [])

    port_dir = os.path.join(PORTS_DIR, name)
    build_dir = os.path.join(port_dir, "build_zimm")

    banner = f"zimmermann {name}"
    if not no_clean:
        shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(build_dir, exist_ok=True)

    t0 = time.perf_counter()
    if not build_ze_build(port_dir, build_dir, zimm_install):
        print(f"FAIL  {banner}: build_ze_build (compile)")
        return False
    t1 = time.perf_counter()

    if not run_ze_build(build_dir):
        print(f"FAIL  {banner}: run_ze_build (generate build.ninja)")
        return False
    t2 = time.perf_counter()

    if not run_ninja(build_dir):
        print(f"FAIL  {banner}: ninja (build)")
        return False
    t3 = time.perf_counter()

    if not verify_artifacts(build_dir, artifacts):
        print(f"FAIL  {banner}: artifact check")
        return False

    t4 = t3
    t5 = t3
    if binary is not None:
        stdout = run_binary(build_dir, binary)
        if stdout is None:
            print(f"FAIL  {banner}: binary exited non-zero or not found")
            return False
        t4 = time.perf_counter()

        if not check_output(stdout, expected):
            print(f"FAIL  {banner}: output mismatch")
            return False
        t5 = time.perf_counter()

    if perf:
        times = [
            f"  build_ze_build: {(t1 - t0) * 1000:.1f}ms",
            f"  run_ze_build:   {(t2 - t1) * 1000:.1f}ms",
            f"  run_ninja:      {(t3 - t2) * 1000:.1f}ms",
        ]
        if binary is not None:
            times.append(f"  run_binary:     {(t4 - t3) * 1000:.1f}ms")
            times.append(f"  check_output:   {(t5 - t4) * 1000:.1f}ms")
        print(f"PASS  {banner}\n" + "\n".join(times))
    else:
        print(f"PASS  {banner}")
    return True


def main() -> int:
    ports = PORTS

    if len(sys.argv) < 2:
        print(
            "usage: build_ports.py <zimmermann-install-path> [--no-clean] [--perf] [--port name1,name2]",
            file=sys.stderr,
        )
        return 1

    zimm_install = os.path.abspath(sys.argv[1])
    if not os.path.isdir(zimm_install):
        print(f"error: zimmermann install path does not exist: {zimm_install}", file=sys.stderr)
        return 1

    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv) and sys.argv[idx + 1]:
            selected = set(sys.argv[idx + 1].split(","))
            ports = [p for p in PORTS if p["name"] in selected]
            if not ports:
                print(f"error: no matching ports for --port {sys.argv[idx + 1]!r}", file=sys.stderr)
                return 1

    perf = "--perf" in sys.argv
    no_clean = "--no-clean" in sys.argv

    failures = 0
    for port in ports:
        if not build_port_cmake(port, no_clean=no_clean, perf=perf):
            failures += 1
        if not build_port_zimmermann(port, zimm_install, no_clean=no_clean, perf=perf):
            failures += 1

    total = len(ports) * 2
    if failures == 0:
        print(f"\nall {total} build(s) passed")
    else:
        print(f"\n{failures}/{total} build(s) FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(main())
