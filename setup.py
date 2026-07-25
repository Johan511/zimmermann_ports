#!/usr/bin/env python3

import configparser
import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PORTS_DIR = os.path.join(SCRIPT_DIR, "ports")


def git_submodule_update():
    print("[setup] pulling submodules...")
    subprocess.run(
        ["git", "submodule", "update", "--init", "--recursive"],
        cwd=SCRIPT_DIR,
        check=True,
    )


def parse_submodules():
    gitmodules_path = os.path.join(SCRIPT_DIR, ".gitmodules")
    if not os.path.exists(gitmodules_path):
        print("[setup] no .gitmodules found, skipping submodule setup")
        return []

    parser = configparser.ConfigParser()
    parser.read(gitmodules_path)
    submodules = []
    for section in parser.sections():
        if section.startswith('submodule "'):
            name = section[len('submodule "') : -1]
            path = parser.get(section, "path")
            submodules.append({"name": name, "path": path})
    return submodules


def apply_patch(submodule):
    patch_name = os.path.basename(submodule["path"]) + ".zimm.patch"
    patch_path = os.path.join(PORTS_DIR, patch_name)
    submodule_path = os.path.join(SCRIPT_DIR, submodule["path"])

    if not os.path.exists(patch_path):
        print(f"[setup] no patch found for {submodule['name']}, skipping")
        return

    if not os.path.exists(submodule_path):
        print(f"[setup] submodule path {submodule_path} not found, skipping")
        return

    print(f"[setup] applying {patch_name} to {submodule['name']}...")
    with open(patch_path, "r") as f:
        subprocess.run(
            ["git", "apply"],
            cwd=submodule_path,
            stdin=f,
            check=True,
        )


def main():
    submodules = parse_submodules()
    for sm in submodules:
        apply_patch(sm)
    print("[setup] done")


if __name__ == "__main__":
    main()
