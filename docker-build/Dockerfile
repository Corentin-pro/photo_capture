FROM ubuntu:xenial

MAINTAINER corentin-pro@mail.com

ADD requirements.txt /tmp/requirements.txt

# install apt-repository
RUN apt-get update && apt-get -y install software-properties-common \
    # install packages
    && apt-get install -y --no-install-recommends \
    python \
    python-dev \
    wget \
    v4l-utils \
    ffmpeg \

    # install pip
    && wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py && rm get-pip.py && pip install --upgrade pip \

    # install library by pip
    && pip install -r /tmp/requirements.txt \

    # cleaning
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/
