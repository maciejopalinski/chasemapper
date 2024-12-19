# -------------------
# The build container
# -------------------
FROM python:3.11-bookworm AS build

# Upgrade base packages.
RUN apt-get update && \
  apt-get upgrade -y && \
  apt-get install -y \
  cmake \
  libgeos-dev \
  libatlas-base-dev && \
  rm -rf /var/lib/apt/lists/*

# Copy in existing wheels.
# COPY wheel[s]/ /root/.cache/pip/wheels/

# No wheels might exist.
RUN mkdir -p /root/.cache/pip/wheels/

# Copy in requirements.txt.
COPY requirements.txt /root/chasemapper/requirements.txt

# Install Python packages.
RUN pip3 install --user --break-system-packages  --no-warn-script-location \
  --ignore-installed -r /root/chasemapper/requirements.txt

# Copy in chasemapper.
COPY . /root/chasemapper

# Download and install cusf_predictor_wrapper, and build predictor binary.
ADD https://github.com/darksidelemm/cusf_predictor_wrapper/archive/master.zip \
  /root/cusf_predictor_wrapper-master.zip
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

# Upgrade base packages and install application dependencies.
RUN apt-get update && \
  apt-get upgrade -y && \
  apt-get install -y \
  libeccodes0 \
  libgeos-c1v5 \
  libglib2.0-0 \
  libatlas3-base \
  libgfortran5 \
  tini && \
  rm -rf /var/lib/apt/lists/*

# Copy any additional Python packages from the build container.
COPY --from=build /root/.local /root/.local

# Copy predictor binary from the build container.
COPY --from=build /root/cusf_predictor_wrapper-master/src/build/pred \
  /opt/chasemapper/

# Copy in chasemapper.
COPY . /opt/chasemapper

# Set the working directory.
WORKDIR /opt/chasemapper

# Ensure scripts from Python packages are in PATH.
ENV PATH=/root/.local/bin:$PATH

# Use tini as init.
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run horusmapper.py.
CMD ["python3", "/opt/chasemapper/horusmapper.py"]
