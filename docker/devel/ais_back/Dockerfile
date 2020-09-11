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
# RUN echo "http://nl.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories \
#     && apk update \
#     && apk add binutils geos gdal proj \
#     && apk add libpq \
#     && apk add --virtual .build-deps gcc python3-dev musl-dev postgresql-dev \
#     && pip install -r /requirements.txt \
#     && apk del .build-deps
RUN apt-get install -y binutils libproj-dev gdal-bin libgeos-dev \
    && apt-get install -y libpq-dev \
    && apt-get install -y gcc python3-dev musl-dev \
    && pip install -r /requirements/dev.txt \
    && apt-get autoremove -y gcc python3-dev musl-dev

COPY ./docker/devel/ais_back/init.sh /init.sh
RUN chmod +x /init.sh && apt-get install -y inetutils-ping

RUN mkdir -p /app/ais \
    && useradd ais

WORKDIR /app/ais
COPY ./ais_back .

RUN chown -R ais:ais .

# RUN echo "GDAL_LIBRARY_PATH='/usr/lib/libgdal.so.20'" >> ais/settings.py

USER ais


# ENTRYPOINT ["/init.sh"]
CMD ["/init.sh","help"]
