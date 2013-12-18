#!/bin/sh

export REDIS_SECRET=somesecretredispasswordisthebomshitdontyouthink

export REGISTRY_USER=dcrtest
export REGISTRY_PASS=1secretpassword
export REGISTRY_EMAIL=io+ops@docker.io

echo REDIS_SECRET = $REDIS_SECRET
echo REGISTRY_USER = $REGISTRY_USER
echo REGISTRY_PASS = $REGISTRY_PASS
echo REGISTRY_EMAIL = $REGISTRY_EMAIL

