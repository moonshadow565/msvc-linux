FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y clang llvm python msitools && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/msvc

COPY install.py vsdownload.py ./

RUN PYTHONUNBUFFERED=1 ./vsdownload.py --accept-license --dest /opt/msvc && \
    ./install.py /opt/msvc /opt/msvc && \
    rm install.py vsdownload.py
