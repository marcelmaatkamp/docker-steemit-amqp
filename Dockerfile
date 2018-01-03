FROM python:3-alpine

RUN apk add --update build-base openssl-dev &&\
 pip3 install steem pika &&\
 rm -rf /var/cache/apk/*

WORKDIR /app
COPY *.py /app/

# ADD anti-comment-bot-bot.py away-trust-friends-bot.py fetch-steamcleaners-commentspam-list.py mute-steamcleaners-commentspam-list.py mycredentials-example.py mycredentials.py -> mycredentials-example.py steempersist.py steemutils.py .
