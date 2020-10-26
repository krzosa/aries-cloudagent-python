aca-py start \
    -it http 0.0.0.0 80 \
    -ot http \
    -ot ws \
    -e $ACAPY_ENDPOINT \
    --label $AGENT_NAME \
    --auto-accept-requests --auto-ping-connection \
    --auto-respond-credential-proposal --auto-respond-credential-offer --auto-respond-credential-request --auto-store-credential \
    --auto-respond-presentation-proposal --auto-respond-presentation-request --auto-verify-presentation \
    --invite --invite-role admin --invite-label "$AGENT_NAME (admin)" \
    --genesis-url $GENESIS_URL \
    --wallet-type indy \
    --wallet-name $AGENT_NAME \
    --admin 0.0.0.0 8150 --admin-insecure-mode \
    --webhook-url ws://websocket_server$1:5000 \
    --plugin acapy_plugin_toolbox \
    --plugin services \
    --log-level INFO 
    