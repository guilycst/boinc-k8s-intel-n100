FROM boinc/client@sha256:a9629c767fcaab695401a2a4a6a34befe087f6cc59a41c51539531eff645e6e2 AS build
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    autoconf automake build-essential ca-certificates git libtool pkg-config \
    libcurl4-openssl-dev libssl-dev libsqlite3-dev libz-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init && git remote add origin https://github.com/BOINC/boinc.git \
    && git fetch --depth=1 origin ef335f4614477b53879af8c1a59f3621f80bdd55 \
    && git checkout --detach FETCH_HEAD
COPY single-gpu-task.patch /tmp/single-gpu-task.patch
RUN git apply --check /tmp/single-gpu-task.patch && git apply /tmp/single-gpu-task.patch \
    && ./_autosetup \
    && ./configure --disable-server --disable-manager --disable-shared --enable-client --disable-nls \
    && make -j2 -C lib && make -j2 -C zip && make -j2 -C client

FROM boinc/client@sha256:a9629c767fcaab695401a2a4a6a34befe087f6cc59a41c51539531eff645e6e2
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    intel-opencl-icd ocl-icd-libopencl1 clinfo \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/client/boinc /usr/bin/boinc
LABEL org.opencontainers.image.source="https://github.com/guilycst/boinc-k8s-intel-n100" \
      org.opencontainers.image.description="BOINC 8.0.4 Intel OpenCL pilot; whole-device GPU task scheduling"
RUN boinc --version && ldd /usr/bin/boinc && ! ldd /usr/bin/boinc | grep 'not found'
COPY verify-client.py verify-residency.py /opt/boinc/
USER 1000:1000
RUN python3 /opt/boinc/verify-client.py && python3 /opt/boinc/verify-residency.py
