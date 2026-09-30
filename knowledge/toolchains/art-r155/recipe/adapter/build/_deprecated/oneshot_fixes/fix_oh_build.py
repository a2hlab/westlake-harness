#!/usr/bin/env python3
"""Auto-fix missing OH component errors in gn gen.
Iteratively runs OH build, detects missing components, adds them to product config."""
import json
import subprocess
import re
import os

OH_DIR = "/root/oh"
CONFIG_FILE = f"{OH_DIR}/vendor/hihope/dayu210/config.json"
BUILD_LOG = f"{OH_DIR}/out/rk3588/build.log"
MAX_ITERATIONS = 30

def get_component_subsystem(component_name):
    """Find subsystem for a component from bundle.json files"""
    for root, dirs, files in os.walk(OH_DIR):
        # Skip deep paths and output dirs
        if '/out/' in root or '/.git/' in root:
            continue
        if "bundle.json" in files:
            path = os.path.join(root, "bundle.json")
            try:
                with open(path) as f:
                    bundle = json.load(f)
                comp = bundle.get("component", {})
                if comp.get("name") == component_name:
                    return comp.get("subsystem", "thirdparty")
            except:
                pass
    return None

def add_component_to_config(component_name, subsystem_name):
    """Add a component to the product config"""
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)

    found = False
    for s in cfg["subsystems"]:
        if s["subsystem"] == subsystem_name:
            for c in s["components"]:
                if c["component"] == component_name:
                    return False
            s["components"].append({"component": component_name, "features": []})
            found = True
            break

    if not found:
        cfg["subsystems"].append({
            "subsystem": subsystem_name,
            "components": [{"component": component_name, "features": []}]
        })

    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    return True

def run_build():
    """Run OH build (will stop at first GN error)"""
    configs_dir = f"{OH_DIR}/out/rk3588/build_configs"
    if os.path.exists(configs_dir):
        subprocess.run(["rm", "-rf", configs_dir])

    result = subprocess.run(
        ["bash", "-c", f"cd {OH_DIR} && ./build.sh --product-name dayu210 --ccache --gn-args allow_sanitize_debug=true 2>&1"],
        capture_output=True, text=True, timeout=600
    )
    return result.stdout + result.stderr

def extract_missing_from_log():
    """Extract missing component from build.log"""
    try:
        with open(BUILD_LOG) as f:
            log = f.read()
        m = re.search(r'OHOS component : \((\w+)\) not found', log)
        if m:
            return m.group(1)
        # Check for assertion failures
        if 'Assertion failed' in log:
            return "__ASSERTION__"
    except:
        pass
    return None

for i in range(MAX_ITERATIONS):
    print(f"\n=== Iteration {i+1} ===")
    output = run_build()

    # Check for success
    if 'build completed' in output.lower() or ('ninja' in output and 'error' not in output.lower()):
        print("BUILD SUCCEEDED!")
        break

    # Check for ninja compilation phase (GN gen passed)
    if '[1/' in output or 'Starting ninja...' in output:
        print("GN gen passed! Ninja compilation started.")
        print(output[-500:])
        break

    missing = extract_missing_from_log()
    if not missing:
        print("  No missing component found. Other error:")
        print(output[-300:])
        break

    if missing == "__ASSERTION__":
        print("  Assertion failure - likely sanitizer or config issue")
        try:
            with open(BUILD_LOG) as f:
                for line in f:
                    if 'Assertion' in line or 'assert' in line.lower():
                        print(f"  {line.strip()}")
        except:
            pass
        break

    print(f"  Missing: {missing}")
    subsystem = get_component_subsystem(missing)
    if subsystem:
        print(f"  Subsystem: {subsystem}")
        if add_component_to_config(missing, subsystem):
            print(f"  -> Added to product config")
        else:
            print(f"  -> Already exists, cannot auto-fix")
            break
    else:
        print(f"  Cannot find bundle.json for '{missing}'")
        break

print("\nDone.")
