FROM python:3.10.7

ARG DISCORD_TOKEN
ARG GIPHY_TOKEN
ARG GIT_HASH
ARG GIT_USER
ARG GIT_PASS

RUN apt-get update \
    && apt-get install -yq tzdata nano \
    && ln -fs /usr/share/zoneinfo/Europe/London /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata

RUN mkdir -vp /home/app

COPY . /home/app/

RUN git config --global url.https://${GIT_USER}:${GIT_PASS}@github.com/.insteadOf https://github.com/

ENV PYTHONPATH=/home/app/

RUN pip install -r home/app/requirements.txt \
    && touch /home/app/discordbot/.env \
    && echo "DEBUG_MODE=0" >> /home/app/discordbot/.env \
    && echo "DISCORD_TOKEN=${DISCORD_TOKEN}" >> /home/app/discordbot/.env \
    && echo "GIPHY_API_KEY=${GIPHY_TOKEN}" >> /home/app/discordbot/.env

WORKDIR /home/app/discordbot

CMD ["python", "/home/app/discordbot/main.py"]
