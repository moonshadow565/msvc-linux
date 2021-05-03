#!/usr/bin/env python3
import sys
import os
import shutil
import glob
import codecs
import re

TEMPLATE_MSVCENV = """#!/usr/bin/env sh
SDK=kits/10
BASE="{BASE}"
MSVCVER="{MSVCVER}"
SDKVER="{SDKVER}"
ARCH="{ARCH}"
MSVCDIR="$BASE/vc/tools/msvc/$MSVCVER"
SDKINCLUDE="$BASE/$SDK/include/$SDKVER"
SDKLIB="$BASE/$SDK/lib/$SDKVER"
SDKBINDIR=$BASE/$SDK/bin/$SDKVER/x64

export INCLUDE="$MSVCDIR/include;$SDKINCLUDE/shared;$SDKINCLUDE/ucrt;$SDKINCLUDE/um;$SDKINCLUDE/winrt"
export LIB="$MSVCDIR/lib/$ARCH;$SDKLIB/ucrt/$ARCH;$SDKLIB/um/$ARCH"
export LIBPATH="$LIB"
"""

TEMPLATE_CL = """#!/usr/bin/env sh
source "{BASE}/bin/{ARCH}/msvcenv.sh"
clang-cl "$@"
"""

TEMPLATE_LINK = """#!/usr/bin/env sh
source "{BASE}/bin/{ARCH}/msvcenv.sh"
lld-link "$@"
"""

TEMPLATE_LIB = """#!/usr/bin/env sh
source "{BASE}/bin/{ARCH}/msvcenv.sh"
llvm-lib "$@"
"""

TEMPLATE_RC = """#!/usr/bin/env sh
source "{BASE}/bin/{ARCH}/msvcenv.sh"
llvm-rc "$@"
"""

TEMPLATE_RUSTENV_HEADER="""#!/usr/bin/env sh
"""

TEMPLATE_RUSTENV = """
export CC_{PLATFORM}="{BASE}/bin/{ARCH}/clang-cl.exe"
export CXX_{PLATFORM}="{BASE}/bin/{ARCH}/clang-cl.exe"
export AR_{PLATFORM}="{BASE}/bin/{ARCH}/lib.exe"
export RC_{PLATFORM}="{BASE}/bin/{ARCH}/rc.exe"
export CARGO_TARGET_{PLATFORM_UPPER}_LINKER="{BASE}/bin/{ARCH}/link.exe"
"""

ARCH_PLATFORMS = {
    "x64": [
        "x86_64_pc_windows_msvc"
    ],
    "x86": [
        "i686_pc_windows_msvc",
        "i586_pc_windows_msvc",
    ],
    "arm64": [
        "aarch64_pc_windows_msvc",
    ]
}

def copy_keep(src_dir, dst_dir, name):
    src = f"{src_dir}/{name}"
    dst = f"{dst_dir}/{name}"
    os.makedirs(dst_dir, exist_ok = True)
    shutil.copy(src, dst)
    os.chmod(dst, 0o644)

def copy_lower(src_dir, dst_dir, name):
    src = f"{src_dir}/{name}"
    dst = f"{dst_dir}/{name.lower()}"
    os.makedirs(dst_dir, exist_ok = True)
    shutil.copy(src, dst)
    os.chmod(dst, 0o644)

def copy_lower_fix_include(src_dir, dst_dir, name):
    src = f"{src_dir}/{name}"
    dst = f"{dst_dir}/{name.lower()}"
    os.makedirs(dst_dir, exist_ok = True)
    with codecs.open(src, "r", encoding="cp1250") as inf:
        with codecs.open(dst, "w", encoding="cp1250") as outf:
            for line in inf.readlines():
                if line.startswith("#include"):
                    line = line.lower()
                    line = line.replace("\\", "/")
                    changed = True
                outf.write(line)
        os.chmod(dst, 0o644)

def get_latest_version(dirname):
    alphanum = lambda key: tuple(int(c) if c.isdigit() else c for c in re.split('(\d+)', key))
    versions = list(sorted(os.listdir(dirname), key = alphanum))
    return versions[-1]

def generate_exe(filename, template, **kwargs):
    dirname = os.path.dirname(filename)
    os.makedirs(dirname, exist_ok = True)
    with open(filename, "w") as outf:
        outf.write(template.format(**kwargs))
    os.chmod(filename, 0o755)

def generate_env(dst, base):
    sdkver = get_latest_version(f"{dst}/kits/10/include")
    msvcver = get_latest_version(f"{dst}/vc/tools/msvc")

    base_kwargs = { 'BASE': base, 'SDKVER': sdkver, 'MSVCVER': msvcver }
    for arch in ARCH_PLATFORMS.keys():
        kwargs = { **base_kwargs, 'ARCH': arch }
        generate_exe(f"{dst}/bin/{arch}/msvcenv.sh", TEMPLATE_MSVCENV, **kwargs)
        generate_exe(f"{dst}/bin/{arch}/clang-cl.exe", TEMPLATE_CL, **kwargs)
        generate_exe(f"{dst}/bin/{arch}/link.exe", TEMPLATE_LINK, **kwargs)
        generate_exe(f"{dst}/bin/{arch}/lib.exe", TEMPLATE_LIB, **kwargs)
        generate_exe(f"{dst}/bin/{arch}/rc.exe", TEMPLATE_RC, **kwargs)

    generate_exe(f"{dst}/bin/rustenv.sh", TEMPLATE_RUSTENV_HEADER, **base_kwargs)
    with open(f"{dst}/bin/rustenv.sh", "a") as outf:
        for arch, platforms in ARCH_PLATFORMS.items():
            for platform in platforms:
                kwargs = { **base_kwargs, 'ARCH': arch, 'PLATFORM': platform, 'PLATFORM_UPPER': platform.upper() }
                outf.write(TEMPLATE_RUSTENV.format(**kwargs))

def install_dir(src, dst, filters):
    for root, dirs, files in os.walk(src, topdown=False):
        root = os.path.relpath(root, src)
        for name in files:
            org_name = f"{root}/{name}".replace("\\", "/")
            for filter_func, copy_func in filters.items():
                if filter_func(org_name):
                    src_dir = f"{src}/{root}".replace("\\", "/")
                    dst_dir = f"{dst}/{root.lower()}".replace("\\", "/")
                    copy_func(src_dir, dst_dir, name)
                    break

def install(src, dst, base):
    copy_filters = {
        re.compile(r"^kits/10/include/[^/]+/(um|shared)/.+", re.IGNORECASE).match : copy_lower_fix_include,
        re.compile(r"^kits/10/(lib|include)/.+", re.IGNORECASE).match : copy_lower,
        re.compile(r"^vc/tools/msvc/[^/]+/(lib|include)/.+", re.IGNORECASE).match : copy_keep,
    }
    install_dir(src, dst, copy_filters)
    generate_env(dst, base)

def run(script, src, dst = ".", prefix = "", *args):
    src =  os.path.abspath(src).replace("\\", "/")
    dst =  os.path.abspath(dst).replace("\\", "/")
    prefix = prefix.replace("\\", "/")
    if prefix:
        install(src, f"{dst}/{prefix}/msvc", f"/{prefix}/msvc")
    else:
        install(src, f"{dst}/msvc", f"{dst}/msvc")

run(*sys.argv)
