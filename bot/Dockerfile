FROM python

RUN apt-get update

WORKDIR /reamance

COPY ./requirements.txt ./requirements.txt

RUN pip3 install --no-cache-dir --disable-pip-version-check -r ./requirements.txt

COPY . .