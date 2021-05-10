import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request 

class Blockchain (object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        #Makes the genesis
        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address):
        """
            Add a new node to the list of nodes
            :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
            :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
            Determine if a given blockchain is valid
            :param chain: <list> A blockchain
            :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n--------------\n")
            #Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            last_block = block
            current_index += 1

        return True
    
    def resolve_conflicts(self):
        """
            This is our Consensus Algorithm, it resolves conflicts
            by replacing our chain with the longest one in the network.
            :return: <bool> True if our chain was replaced, False if not
        """

        neighbours = self.nodes
        new_chain = None

        #Looking for a chain longer than ours
        max_length = len(self.chain)

        response = request.get(f'http://{node}/chain')

        if response.status_code == 200:
            length = response.json()['length']
            chain = response.json()['chain']

            #Check if the length is longer and the chain is valid
            if length > max_length and self.valid_chain(chain):
                max_length = length
                new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """
            Create a new block
            :param proof: <int> Proof given by prrof of work algo
            :param previous_hash: (Optional) <str> Hash of previous block
            :return: <dict> New block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        #Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """
            Creates a new transaction to go into a block
            :param sender: <str> Adress of sender
            :param recipient: <str> Address of the recipient
            :param amount: <int> Amount of coin
            :return: <int> Index of block that will hold the transaction
        """
        
        self.current_transactions.append({
            'sender':sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
            Creates a SHA-256 hash of a block
            :param block: <dict> block
            :return: <str>
        """
        
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
            Simple pow algo
            - Find a number p such that hash(a+p) contains leading 4 zeros, where a is the previous p
            -a is the previous proof, and p is the new proof
            :param last_proof: <int>
            :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
            Validates the proof: does hash(last_proof, proof) contain 4 leading zeros
            :param last_proof: <int> previous proof
            :param proof: <int> Current proof
            :return: <bool> True if correct, falsi if not
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

#Instantiate our node
app = Flask(__name__)

#generate a globally unique adress for this node 
node_identifier = str(uuid4()).replace('-', '')

#Instatntiate the blockchain
blockchain = Blockchain()

@app.route('/mine', methods=['GET'])
def mine():
        last_block = blockchain.last_block
        last_proof = last_block['proof']
        proof = blockchain.proof_of_work(last_proof)

        #We must recieve a reward for finding the proof
        # The sender is 0 to signify that this node has mined a new coin
        blockchain.new_transaction(
            sender="0",
            recipient=node_identifier,
            amount=1,
        )

        #Forge the new block by adding it to teh chain
        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)

        response = {
            'message': "New block forged",
            'index': block['index'],
                'transactions': block['transactions'],
                'proof': block['proof'],
                'previous_hash': block['previous_hash'],
        }
        return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
        values = request.get_json()

        #Check that the required fields are in the posted data
        required = ['sender', 'recipient', 'amount']
        if not all(k in values for k in required):
            return 'Missing values', 400

        #Create a new transaction
        index = blockchain.new_transaction(
            values['sender'], values['recipient'], values['amount'])

        response = {'message': f'Transaction will be added to block {index}'}
        return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
        response = {
            'chain': blockchain.chain,
            'length': len(blockchain.chain),
        }
        return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if  nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
            'message': 'New nodes have been added',
            'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
                'message': 'Our chain was replaced',
                'new_chain': blockchain.chain
        }
    else:
        response = {
                'message': 'Our chain is authoritative',
                'chain': blockchain.chain
        }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
