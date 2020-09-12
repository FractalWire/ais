FROM elixir:slim

RUN apt-get update \
    && apt-get install -y locales \
    && echo 'fr_FR.UTF-8 UTF-8' > /etc/locale.gen \
    && echo 'en_US.UTF-8 UTF-8' >> /etc/locale.gen \
    && locale-gen
ENV LANG fr_FR.UTF-8
ENV LC_ALL fr_FR.UTF-8

RUN apt-get install -y netcat inotify-tools curl \
    && (curl -sL https://deb.nodesource.com/setup_14.x | bash -) \
    && apt-get install -y nodejs

WORKDIR /app
RUN mix do local.hex --force, local.rebar --force

COPY ./docker/devel/ais_front/init.sh /init.d/init.sh
COPY ./docker/common/init.d/*.sh /init.d/
RUN chmod +x /init.d/*.sh

CMD ["/init.d/init.sh"]
