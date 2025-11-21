# bootdotdev.backbone

**Spec Version:** 0.1.2
**Code Version:** 0.1.8

Personal Project for Boot.dev: A simple server-client framework for client-client communication (read "chat") losely based on SSH with private-key authentication written in Python.

This project is intended as an excercise in:
- Socket-based communication
- Multi-threading
- Public-Private key cryptography

## Basic Concepts

1. Backbone Server:
   - Holds a Public-Private key-pair for server identification and connection encryption.
   - Holds a list of valid client IDs (UUID4s) and public keys (RSA).
   - Generates public and private keys for new clients.
   - Listens for connections from clients.
   - Validates client connection details.
   - Holds a list of client connections.
   - Accepts and routes Client-Client messages from clients to other clients.
   - Sends Server-Client messages to clients to:
     - Post server state changes.
   - Monitors client heartbeat and handles dead clients.
  
2. Backbone Client:
   - Holds a private key and ID assgned by a server.
   - Connects to the a single server.
   - Sends Client-Client messages to other clients.
   - Receives Client-Client messages from other clients.
   - Sends Client-Server messages to:
     - Control connection state.
     - Request server status.
     - Request connection status for clients.
     - Provide heartbeat status to the server.
   - Receives Server-Client messages.

3. Client-Client Message:
   - Contains a Receiver Address.
   - Contains message data length.
   - Contains implementation-specific data. The receiving client(s) is/are expected to know how to interpret the data, .

4. Client-Server message:
   - Contains one of:
     - Connection state change request.
     - Client status query.
     - Server status query
     - Heartbeat info.
  
5. Server-Client Message:
   - Contains:
     - Server state change information.
     - Connection settings change information

6. Connection Settings:
   - Contains:
     - Heartbeat Interval
     - Connection Timeout

7. Client ID: A Univerally Unique ID version 4 (UUIDv4)


## Specifications

### Connection

**Preconditions**
- Each client holds:
  -  _client ID_
  -  _client private key_
- The server holds
  - A _server private key_
  - A _server public key_
  - A record with:
    - _client ID_
    - _client public key_
- All communication except the initial _challenge_ should be encrypted using the corresponding _server public key_ or _client public key_.

#### Authentication flow

Each client is expected to establish and maintain a connection with the server via TCP.

Once a connection has been established, the server will issue a challenge by transmitting an amount of binary data (_challenge data_) and a pulic key (_server_pub_key_).

In order to authenticate the connection, the client should generate a _signature_ using its pre-assigned private key and algorithm, which it then transmits via the TCP connection along with it's pre-assigned client_id to indicate which _client public key_ should be used to verify the signature.

If the client responds within the _connection timout_, the server will attempt to verify the signature using the _client public key_ and _challenge data_and transmit the .

If the client fails to respond within the _connection timeout_, the _client ID_ is unknown to the server or the signature cannot be verified, the server should close the connection.

##### Successful authentication
```
                                     Client                                   Server
1:                                   | <-- <server_pub_key challenge_data> -- |
2: sign(private_key, challenge_data) |                                        | 
3:                                   | -- <client_id & signature> ----------> |
4:                                   |                                        | Verify(clients[client_id][key], challenge_data, signature) == true
5:                                   |                                        | client[client_id].connected = true
6:                                   |                                        | client[client_id].sign_of_life = Utc::now()
7:                                   | <------------- <cnnection settings> -- |
8:                                   |                                        | // Wait for message or timout (settings.timeout < (Utc::Now() - client[client_id].sign_of_life)).
```

### Message Format
All messages are expected to be binary data, with the first 2 bytes being the length of the _payload data_ (in bytes).

The _payload data_ should be one of:
- challenge
- response
- Client-Client (C2C)
- Client-Server (C2S)
- Server-Client (S2C)

For all formats other than _challenge_, the _payload data_ should be encrypted.

```
Bytes  | Field
--------------
0:1    | Message size
2:N    | Payload data (Encrypted)
```

#### Challenge & Response
Backbone uses a challenge/response system for authentication:
1. The first packet sent across the socket is a _challenge_ (containing the server's public key and the a randomized set of data).
2. The second packet should be the client's _response_ (containing the client's ID and a signature for the randomized data in the challenge).

Challenge Payload:
```
Bytes          | Field
----------------------
0:1            | Key Size (key_size, max 65KiB) 
2:2+key_size   | Payload data (Encrypted)
2+key_size:N   | Challenge data (challenge_data)
```

_Challenge data_ should be _settings.challenge_size_ bytes (default 256) of randomized data. This is done to prevent caching of response data.

Response Payload:
```
Bytes | Field
-------------
0:16  | Client ID (client_id)
16:N  | Signature
```

#### C2C, C2S & S2C
All message types are are either client-to-client (c2c), client-to-server (c2s) or server-to-client (s2c).

Prior to message processing, the _payload data_ must be decrypted into _message data_ using the _server private key_ or _client private key_.

The first 2 bits of the _message data_ are reserved to indicate the type of message:
- 0: c2c
- 1: c2s or s2c
- 2-3: Reserved for future use

```
Bytes  | Field
-------------
0[0:1] | Message type (0=Client-Client, 1=Server-Client or Client-Server)
```

##### Client-to-Client (C2C)
C2C messages are meant to be routed between clients, and so the majority of the _message data_ is reserved for client-defined data.

The first 16 bytes indicate the recipient client ID.

```
Bytes          | Field
----------------------
0[2:7]:15[0:1] | Recipient ID
15[2:7]        | Reserved
16:N           | C2C data
```
