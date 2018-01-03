# Steemit in amqp

## Credentials file

Create a `credentials.py`:

```
keys=["POSTING KEY FROM https://steemit.com/@username/permissions"]
account="username"
friends=["friend1","friend2"]
```

# Start ingest

```
$ docker-compose up -d rabbitmq
$ docker-compose run amqp
```
