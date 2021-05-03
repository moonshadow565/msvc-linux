FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y clang-11 llvm-11 lld-11 python3 msitools ca-certificates && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/msvc

COPY install.py vsdownload.py ./

RUN PYTHONUNBUFFERED=1 \
    ./vsdownload.py --accept-license --dest /opt/msvc \
        Microsoft.VisualStudio.Component.Windows10SDK.19041 \
        Microsoft.VisualStudio.Component.VC.14.28.x86.x64 && \
    ./install.py /opt/msvc --llvm 11 --archs x86,x64
