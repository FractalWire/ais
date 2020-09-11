FROM mdillon/postgis:11

# Changes locales, additional steps might be required
RUN apt-get update \
    && apt-get install -y locales \
    && echo 'fr_FR.UTF-8 UTF-8' > /etc/locale.gen \
    && echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen \
    && locale-gen
ENV LANG fr_FR.UTF-8
ENV LC_ALL fr_FR.UTF-8

COPY ./docker/prod/postgres/*.sql /docker-entrypoint-initdb.d/
