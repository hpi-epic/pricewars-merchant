#!/usr/bin/env bash

if [ -z "$MERCHANT_FILE" ]; then
    MERCHANT_FILE="machine_learning/MLmerchant.py"
fi
printf "Using merchant server: %s.\n" "$MERCHANT_FILE"

if [ -z "$MERCHANT_NAME" ]; then
    MERCHANT_NAME="Price Wars Trooper"
fi
printf "Set merchant name to '%s'.\n" "$MERCHANT_NAME"

if [ -z "$MERCHANT_AL_NAME" ]; then
    MERCHANT_AL_NAME="Logistic Regression"
fi
printf "Set merchant algorithm name to '%s'.\n" "$MERCHANT_AL_NAME"

if [ -z "$MERCHANT_IP" ]; then
    MERCHANT_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | tail -n1)
    if [ `echo $MERCHANT_IP | wc -l` -lt 1 ]; then
      echo "Falling back to IP 127.0.0.1"
      MERCHANT_IP="127.0.0.1"
    fi
fi
if [ -z "$MERCHANT_PORT" ]; then
    MERCHANT_PORT=5017
fi
printf "Registering merchant under %s:%d.\n" "$MERCHANT_IP" "$MERCHANT_PORT"


REQ_CMD="curl -s -H \"Content-Type: application/json\" -d '{\"api_endpoint_url\": \"http://$MERCHANT_IP:$MERCHANT_PORT\", \"merchant_name\": \"$MERCHANT_NAME\", \"algorithm_name\": \"$MERCHANT_AL_NAME\", \"nextState\": \"init\", \"marketplace_url\": \"http://marketplace:8080\"}' http://marketplace:8080/merchants"
REQ=`eval $REQ_CMD`

TOKEN=$(echo $REQ | python3 -c "import sys, json; print(json.load(sys.stdin)['merchant_token'])")
printf "Token used for merchant: '%s'.\n" "$TOKEN"

sed "s/{{API_TOKEN}}/$TOKEN/" $MERCHANT_FILE > ${MERCHANT_FILE}_tmp.py

(echo 'Merchant will be activated in 10 second.'; sleep 10; echo 'Activating merchant.'; curl -s -H "Content-Type: application/json" -d '{"nextState": "start"}' http://$MERCHANT_IP:$MERCHANT_PORT/settings/execution) &

echo 'Starting merchant.'
python3 ${MERCHANT_FILE}_tmp.py --port $MERCHANT_PORT

