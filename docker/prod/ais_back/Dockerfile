# FROM python:3.7-alpine
FROM python:3.7-slim

ENV PYTHONUNBUFFERED 1

# Changes locales, additional steps might be required
RUN apt-get update \
    && apt-get install -y locales \
    && echo 'fr_FR.UTF-8 UTF-8' > /etc/locale.gen \
    && echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen \
    && locale-gen
ENV LANG fr_FR.UTF-8
ENV LC_ALL fr_FR.UTF-8

# update system and install requirements
COPY ./ais_back/requirements /requirements
RUN apt-get install -y binutils libproj-dev gdal-bin libgeos-dev \
    && apt-get install -y libpq-dev \
    && apt-get install -y gcc python3-dev musl-dev \
    && pip install -r /requirements/dev.txt \
    && apt-get autoremove -y gcc python3-dev musl-dev

COPY ./docker/prod/ais_back/init.sh /init.d/init.sh
COPY ./docker/common/init.d/*.sh /init.d/
RUN chmod +x /init.d/*.sh
RUN apt-get install -y netcat

RUN mkdir -p /app/ais \
    && useradd ais

WORKDIR /app/ais
COPY ./ais_back .

RUN chown -R ais:ais .

USER ais

CMD ["/init.d/init.sh","help"]
