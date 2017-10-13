# start from steelscript base
FROM riverbed/steelscript
MAINTAINER Riverbed Technology

# tshark needs special noninteractive flag
RUN set -ex \
        && install=' \
                git \
                less \
                vim \
                tshark \
        ' \
        && apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y $install --no-install-recommends \
        && rm -rf /var/lib/apt/lists/*

# auto-reloading monitor
RUN set -ex \
        && cd /tmp && wget https://github.com/cortesi/modd/releases/download/v0.4/modd-0.4-linux64.tgz \
        && tar xvzf modd-0.4-linux64.tgz \
        && mv modd-0.4-linux64/modd /usr/local/bin/modd \
        && chown root:staff /usr/local/bin/modd \
        && rm -rf /tmp/*

# wsgi and db access and progressd
RUN set -ex \
        && pip install psycopg2 gunicorn \
        && pip install reschema==0.5.1 flask==0.10.1 flask_restful==0.3.2 \
        && rm -rf ~/.cache

# install from dev repo in editable mode
# appfwk needs to be installed separately to ensure dependency gets picked up
# for other two packages
RUN set -ex \
        && pip install --src /src -e git+https://github.com/riverbed/steelscript-appfwk#egg=steelscript-appfwk \
        && pip install --src /src \
            -e git+https://github.com/riverbed/steelscript-appfwk-business-hours#egg=steelscript-appfwk-business_hours \
            -e git+https://github.com/riverbed/steelscript-stock#egg=steelscript-stock \
        && rm -f /src/pip-delete-this-directory.txt \
        && rm -rf ~/.cache

