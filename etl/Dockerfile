FROM python:3.9

RUN apt-key del 7fa2af80
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu1804/x86_64/3bf863cc.pub
RUN apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu1804/x86_64/7fa2af80.pub
RUN apt-get update && apt-get install -y \
    git libhdf5-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache numpy==1.26.4 \
    && pip install --no-cache Cython==0.29.37 \
    && pip install --no-cache pandas==1.1.5 --no-build-isolation \
    && pip install -r /code/requirements.txt

RUN python -c 'import tensorflow_hub as hub; hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")'

WORKDIR /code
