# This Dockerfile constructs a docker image, based on the vistalab/freesurfer
# docker image to execute recon-all as a Flywheel Gear.
#
# Example build:
#   docker build --no-cache --tag scitran/freesurfer-recon-all `pwd`
#
# Example usage:
#   docker run -v /path/to/your/subject:/input scitran/freesurfer-recon-all
#
FROM ubuntu:focal

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
RUN mkdir -p ${FLYWHEEL}
WORKDIR ${FLYWHEEL}

ENV DEBIAN_FRONTEND=noninteractive
RUN apt update --fix-missing \
 && apt install -y wget bzip2 ca-certificates \
      libglib2.0-0 \
      libxext6 \
      libsm6 \
      libxrender1 \
      git \
      mercurial \
      subversion \
      curl \
      grep \
      sed \
      dpkg \
      gcc \
      g++ \
      libeigen3-dev \
      zlib1g-dev \
      libgl1-mesa-dev \
      libfftw3-dev \
      libtiff5-dev
RUN apt install -y \
      libxt6 \
      libxcomposite1 \
      libfontconfig1 \
      libasound2 \
      bc \
      tar \
      zip \
      unzip \
      tcsh \
      libgomp1 \
      python3-pip \
      perl-modules

####################################



############################
# Install dependencies
ARG DEBIAN_FRONTEND=noninteractive
RUN apt update && apt install -y \
    xvfb \
    xfonts-100dpi \
    xfonts-75dpi \
    xfonts-cyrillic \
    python \
    imagemagick \
    wget \
    subversion\
    vim

# Install Freesurfer
RUN wget -N -qO- ftp://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/7.3.2/freesurfer-linux-ubuntu20_amd64-7.3.2.tar.gz | tar -xz -C /opt && chown -R root:root /opt/freesurfer && chmod -R a+rx /opt/freesurfer


############################
# Install mamba
ENV CONDA_DIR /opt/conda
ENV MAMBA_ROOT_PREFIX="/opt/conda"
RUN wget --quiet https://github.com/conda-forge/miniforge/releases/latest/download/Mambaforge-$(uname)-$(uname -m).sh -O ~/mamba.sh && \
      /bin/bash ~/mamba.sh -b -p /opt/conda

# Put conda in path so we can use conda activate
ENV PATH=$CONDA_DIR/bin:$PATH

RUN mamba update -n base --all

# install conda env
COPY conda_config/scientific.yml .
RUN mamba env create -f scientific.yml

RUN apt update && apt install -y jq

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
RUN mkdir -p ${FLYWHEEL}

# Copy and configure run script and metadata code
COPY bin/run \
	bin/run.py \
	scripts/stim_as_nii.py    \
	scripts/nii_to_surfNii.py \
	scripts/link_stimuli.py    \
      ${FLYWHEEL}/

# Handle file properties for execution
RUN chmod +x \
      ${FLYWHEEL}/run \
      ${FLYWHEEL}/run.py \
	${FLYWHEEL}/stim_as_nii.py    \
	${FLYWHEEL}/nii_to_surfNii.py \
	${FLYWHEEL}/link_stimuli.py
WORKDIR ${FLYWHEEL}
# Run the run.sh script on entry.
ENTRYPOINT ["/flywheel/v0/run"]

#make it work under singularity
# RUN ldconfig: it fails in BCBL, check Stanford
#https://wiki.ubuntu.com/DashAsBinSh
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
