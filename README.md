# Blockchain
A basic blockchain, with a POW and consensus, that accepts http requests coded in python

Endpoints

/mine [GET]

For mining new blocks

/transactions/new [POST]

For creating new transactions to be appended to the current block 
- Format {
    "sender": "public key"
    "recipient": "public key"
    "amount": 0000
}

/chain [GET]

For getting the full chain that has been mined

/nodes/register [POST]

For registering a node
-Format {
    "nodes": ["http://127.0.0.1:adress"]
}

/nodes/resolve [GET]

For updating current nodes blockchain with the longest blockchain

