#!/usr/bin/env python3
import argparse
import sys
import os
import shutil
import glob
import codecs
import re


TEMPLATE_MSVCENV = """#!/usr/bin/env bash
BASE="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/../.." && pwd)"
MSVCDIR="$BASE/vc/tools/msvc/{MSVCVER}"
SDKINCLUDE="$BASE/kits/10/include/{SDKVER}"
SDKLIB="$BASE/kits/10/lib/{SDKVER}"
export INCLUDE="$MSVCDIR/include;$SDKINCLUDE/shared;$SDKINCLUDE/ucrt;$SDKINCLUDE/um;$SDKINCLUDE/winrt"
export LIB="$MSVCDIR/lib/{ARCH};$SDKLIB/ucrt/{ARCH};$SDKLIB/um/{ARCH}"
export LIBPATH="$LIB"
"""

TEMPLATE_CL = """#!/usr/bin/env bash
source "$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)/msvcenv.sh"
clang-cl{LLVM} "$@"
"""

TEMPLATE_LINK = """#!/usr/bin/env bash
source "$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)/msvcenv.sh"
lld-link{LLVM} "$@"
"""

TEMPLATE_LIB = """#!/usr/bin/env bash
source "$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)/msvcenv.sh"
llvm-lib{LLVM} "$@"
"""

TEMPLATE_RC = """#!/usr/bin/env bash
source "$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)/msvcenv.sh"
llvm-rc{LLVM} "$@"
"""

TEMPLATE_RUSTENV_HEADER="""#!/usr/bin/env bash
BASE_BIN="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
"""

TEMPLATE_RUSTENV = """
export CC_{PLATFORM}="$BASE_BIN/{ARCH}/clang-cl.exe"
export CXX_{PLATFORM}="$BASE_BIN/{ARCH}/clang-cl.exe"
export AR_{PLATFORM}="$BASE_BIN/{ARCH}/lib.exe"
export RC_{PLATFORM}="$BASE_BIN/{ARCH}/rc.exe"
export CARGO_TARGET_{PLATFORM_UPPER}_LINKER="$BASE_BIN/{ARCH}/link.exe"
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
    if not src == dst:
        shutil.copy(src, dst)
    os.chmod(dst, 0o644)
    return dst

def copy_lower(src_dir, dst_dir, name):
    src = f"{src_dir}/{name}"
    dst = f"{dst_dir}/{name.lower()}"
    if not src == dst:
        shutil.copy(src, dst)
    os.chmod(dst, 0o644)
    return dst

def copy_include_lower(src_dir, dst_dir, name):
    src = f"{src_dir}/{name}"
    dst = f"{dst_dir}/{name.lower()}"
    lines = []
    with codecs.open(src, "r", encoding="cp1250") as inf:
        for line in inf.readlines():
            if line.startswith("#include"):
                line = line.replace("\\", "/").lower()
            lines.append(line)
    with codecs.open(dst, "w", encoding="cp1250") as outf:
        for line in lines:
            outf.write(line)
    os.chmod(dst, 0o644)
    return dst

def install_dir(src, dst, filters):
    done = set()
    for root, dirs, files in os.walk(src):
        root = os.path.relpath(root, src)
        for name in files:
            org_name = f"{root}/{name}".replace("\\", "/")
            for filter_func, copy_func in filters.items():
                if filter_func(org_name):
                    src_dir = f"{src}/{root}".replace("\\", "/")
                    dst_dir = f"{dst}/{root.lower()}".replace("\\", "/")
                    os.makedirs(dst_dir, exist_ok = True)
                    done_name = copy_func(src_dir, dst_dir, name)
                    done.add(done_name)
                    break

    if src == dst:
        for root, dirs, files in os.walk(dst, topdown=False):
            for name in files:
                filename = f'{root}/{name}'.replace("\\", "/")
                if not filename in done:
                    os.remove(filename)
            for name in dirs:
                dirname = f'{root}/{name}'.replace("\\", "/")
                if not os.listdir(dirname):
                    os.rmdir(dirname)

def get_latest_version(dirname):
    alphanum = lambda key: tuple(int(c) if c.isdigit() else c for c in re.split('(\d+)', key))
    versions = list(sorted(os.listdir(dirname), key = alphanum))
    return versions[-1]

def generate_exe(filename, mode, template, **kwargs):
    with open(filename, mode) as outf:
        outf.write(template.format(**kwargs))
    os.chmod(filename, 0o755)

def generate_env(dst, llvm):
    base_kwargs = {
        'LLVM': f"-{llvm}" if llvm else "",
        'SDKVER': get_latest_version(f"{dst}/kits/10/include"),
        'MSVCVER': get_latest_version(f"{dst}/vc/tools/msvc"),
    }
    os.makedirs(f"{dst}/bin", exist_ok = True)
    generate_exe(f"{dst}/bin/rustenv.sh", "w", TEMPLATE_RUSTENV_HEADER, **base_kwargs)
    for arch, platforms in ARCH_PLATFORMS.items():
        arch_kwargs = { **base_kwargs, 'ARCH': arch }
        os.makedirs(f"{dst}/bin/{arch}", exist_ok = True)
        generate_exe(f"{dst}/bin/{arch}/msvcenv.sh", "w", TEMPLATE_MSVCENV, **arch_kwargs)
        generate_exe(f"{dst}/bin/{arch}/clang-cl.exe", "w", TEMPLATE_CL, **arch_kwargs)
        generate_exe(f"{dst}/bin/{arch}/link.exe", "w", TEMPLATE_LINK, **arch_kwargs)
        generate_exe(f"{dst}/bin/{arch}/lib.exe", "w", TEMPLATE_LIB, **arch_kwargs)
        generate_exe(f"{dst}/bin/{arch}/rc.exe", "w", TEMPLATE_RC, **arch_kwargs)
        for platform in platforms:
            platform_kwargs = { **arch_kwargs, 'PLATFORM': platform, 'PLATFORM_UPPER': platform.upper() }
            generate_exe(f"{dst}/bin/rustenv.sh", "a", TEMPLATE_RUSTENV, **platform_kwargs)

def install(src, dst, llvm=""):
    src =  os.path.abspath(src).replace("\\", "/")
    dst =  os.path.abspath(dst).replace("\\", "/")
    copy_filters = {
        re.compile(r"^kits/10/include/[^/]+/(um|shared)/.+", re.IGNORECASE).match : copy_include_lower,
        re.compile(r"^kits/10/lib/[^/]+/(um|shared)/.+", re.IGNORECASE).match : copy_lower,
        re.compile(r"^kits/10/(include|lib)/.+", re.IGNORECASE).match : copy_keep,
        re.compile(r"^vc/tools/msvc/[^/]+/(lib|include)/.+", re.IGNORECASE).match : copy_keep,
    }
    install_dir(src, dst, copy_filters)
    generate_env(dst, llvm)

parser = argparse.ArgumentParser(description='Install msvc')
parser.add_argument('src', type=str, help='msvc source files from vsdownload.py')
parser.add_argument('dst', type=str, help='destination directory')
parser.add_argument('-l', '--llvm', type=str, default="", help='optional llvm/clang version suffix(example: "-l 12")')
args = parser.parse_args()
install(args.src, args.dst, args.llvm)
