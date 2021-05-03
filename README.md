Cross compilation with MSVC on Linux
====================================

This is a reproducible Dockerfile for cross compiling with MSVC on Linux,
usable as base image for CI style setups.

This downloads and unpacks the necessary Visual Studio components using
the same installer manifests as Visual Studio 2017/2019's installer
uses. Downloading and installing it requires accepting the license,
available at https://go.microsoft.com/fwlink/?LinkId=2086102 for the
currently latest version.

As Visual Studio isn't redistributable, the resulting docker image isn't
either.

Build the docker image like this:

    docker build .

After building the docker image, there are 4 directories with tools,
in `/opt/msvc/bin/<arch>`, for all architectures out of `x86`,
`x64`, `arm` and `arm64`, that can be added to the PATH before building
with it.

The installer scripts also work fine without docker; just run the following two commands:

    ./vsdownload.py --dest <source dir>
    ./install.py <source dir> <optional destination dir> -l <optional llvm/clang version suffix>

The unpacking requires recent versions of msitools (0.98) and libgcab
(1.2); sufficiently new versions are available in e.g. Ubuntu 19.04.

--------

## Setting up this toolchain for easy cross-compilation in Rust

With this toolchain, cross-compiling rust code has never been easier. Here's
what you need to do to get setup:

1. Install this toolchain, e.g. `./vsdownload.py --dest /opt/msvc && ./install.py /opt/msvc`. You can install it anywhere.
2. Install `clang`, `llvm-lib`, `lld` and `llvm-rc`:
    - `clang` will be used to compile any C dependencies you may have with the
      `cc` crate. Windows officially supports building `msvc` binaries in clang
      since 2019, so it should handle sdk headers and libraries just fine.
   - `lld-link` will be used to link rust executables
   - `llvm-lib` will be used to statically link code when using the `cc` crate.
     It generates `.lib` files compatible with the windows linker.
   - `llvm-rc` will be used to compile resource files (used to add manifests and
     icons to an executable) with the `embed-resource` crate. This will also
     generate `.lib` files.
3. In your shell, source the following script:
    ```
    source /opt/msvc/bin/rustenv.sh
    ```

Congratulations, you're now all set!
