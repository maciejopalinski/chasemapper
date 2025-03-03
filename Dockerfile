FROM python:3.11-bookworm AS build

# Upgrade base packages.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y cmake libgeos-dev libatlas-base-dev && \
    rm -rf /var/lib/apt/lists/*

# Download cusf_predictor_wrapper
ADD https://github.com/darksidelemm/cusf_predictor_wrapper/archive/master.zip /root/cusf_predictor_wrapper-master.zip

# Extract and build cusf_predictor_wrapper
RUN unzip /root/cusf_predictor_wrapper-master.zip -d /root && \
    rm /root/cusf_predictor_wrapper-master.zip && \
    mkdir -p /root/cusf_predictor_wrapper-master/src/build && \
    cd /root/cusf_predictor_wrapper-master/src/build && \
    cmake .. && \
    make

# -------------------------
# The application container
# -------------------------
FROM python:3.11-bookworm

EXPOSE 5001/tcp

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y libeccodes0 libgeos-c1v5 libglib2.0-0 libatlas3-base libgfortran5 tini && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/chasemapper

# Generate self-signed certificate
RUN openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 3650 -nodes -subj "/CN=localhost"

# Copy in existing wheels.
COPY wheel[s]/ /root/.cache/pip/wheels/
# No wheels might exist.
RUN mkdir -p /root/.cache/pip/wheels/

COPY requirements.txt ./
RUN pip3 install --user --break-system-packages  --no-warn-script-location --ignore-installed -r requirements.txt

# Copy predictor binary from the build container.
COPY --from=build /root/cusf_predictor_wrapper-master/src/build/pred ./

# Copy in chasemapper.
COPY . .

# Ensure scripts from Python packages are in PATH.
# ENV PATH=/root/.local/bin:$PATH

# Use tini as init.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run horusmapper.py.
CMD ["python3", "/opt/chasemapper/horusmapper.py", "-v"]