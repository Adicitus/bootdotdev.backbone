# bootdotdev.backbone
**Spec Version:** 0.1.9
**Code Version:** 0.1.28

Personal Project for Boot.dev: A simple server-client framework for client-client communication (read "chat") losely based on SSH with private-key authentication written in Python.

This project is intended as an excercise in:
- Socket-based communication
- Multi-threading
- Public-Private key cryptography

## Why not use TLS/SSL (Lib/ssl.py)?
This is specification is intended as an excercise in using cryptographic primitives to secure communication and data.

### Security implications (why you usually shouldn't do this)
Crucially, Backbone does not provide a chain of trust: the server public key is provided to you as-is.

Under SSL and TLS, connections are secured using X509 certificates: a public key with attached meta-data, signed by a trusted third party private key to guarantee the integrity of the data. This data includes an address (or set of addresses) that you can use to connect to the server.

A certificate associated with that trusted third party key can then be pre-distributed to let the connecting party verify that the certificate provided by the certificate is valid for that address.

Without this mechanism you can become vulnerable to [man-in-the-middle attacks](https://en.wikipedia.org/wiki/Man-in-the-middle_attack), where a third-party server can interpose themselves between you and the target server, pretending to be the target server.

Backbone attempts to mitigates this risk by only using the same public key used for authentication when communicating with the client, however:

1. The client (**C**) attempts a  connect with the target server (**TS**).
2. The deceptive server (**DS**) sits between **C** and **TS**, and accepts the connection in place of **TS**.
3. **DS** initiates a TCP connection to **TS**.
4. **TS** sends a _challenge_ to **DS**
5. **DS** replaces the _server public key_ with its own _deceptive public key_ and sends this _deceptive challenge_ to **C**.
6. **C** uses its private key to sign the _challenge data_ to create a _signature_.
7. **C** encrypts the _signature_ using the _deceptive public key_ and sends it to **DS**
8. **DS** decrypts the _signature_ using its own private key
9. **DS** re-encrypts the _signature_ using the _server public key_ and sends it to **TS**
10. **TS** validates the signature using its stored _client public key_ for **C**.
11. **TS** acccepts the session from **C** and uses the _client public key_ to encrypt all communication with **C** going forward.

Note that this that while **DS** cannot read messages sent by the **TS**, it can still read any messages sent by **C**. This is not acceptable.

This could be further mitigated by having the client sign <ins>both</ins> the _server public key_ and _challenge data_ to verify receipt, either:
1. Client creates separate signatures for the _server public key_ and _challenge data_.
   - This way the server can differentiate between a man-in-the-middle scenario and a login attempt using an invalid private key.
   - However this also lets the attacker cache the _server public key_ signature, which could then be re-used the next time the client tries to connect to the server. This way the attacker can attempt to supplant the _server public key_ with its own _deceptive public key_.
     - This could be mitigated by using a random value provided by the server (see [salt](https://en.wikipedia.org/wiki/Salt_(cryptography)), ["number-used-once"](https://en.wikipedia.org/wiki/Cryptographic_nonce)) to introduce an element of randomness to the signature.
     - <ins>**Please note**</ins> that while the _challenge data_ could be used for this, it would create 2 signatures using the same random element and subsequently theoretically increase the risk of the private key beiong compromised.
2. Client creates a single signature based on _server public key_ and _challenge data_
   - We prevent caching of the _public key_ signature and minimize the risk of the client private key being compromised by guessing based on signatures of known data.
   - Downside is that the server has no way of differentiating between a man-in-the-middle attack and a invalid login attempt.

Specifications prior to version 0.2.0 will NOT define any form of _server public key_ signing mititgation.

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

8. Client Handler: An individual thread on the server used to manage an authenticated _Backbone Client_.

9. Client connection: A socket connection to a _Backbone Client_.

10. Client Queue: A queue maintained by the _Backbone Server_ to deliver messages to a _Client Handler_.

11. Server Queue: A queue maintained by the _Backbone Server_ to deliver messages from _Client Handlers_ to the main thread.


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
- challenge: Unencrypted message with data used to authenticate the client
- response: Signed data and client_id to complete authentication
- Client-Client (C2C): Message routed between clients by the server.
- Client-Server (C2S): Message sent by the client to request information or modify the connection.
- Server-Client (S2C): Message sent as response to a message or to inform the client of changes to the server.
- Server-Server (S2S): Message used to communicate internally with components in the server.

For all formats other than _challenge_, the _payload data_ should be encrypted.

```
Bytes  | Field
--------------
0:1    | Message size
2:N    | Payload data (Encrypted)
```

#### Challenge & Response
Backbone uses a challenge/response system for authentication:
1. The first packet sent across the socket is a _challenge_ (containing the _server public key_ and the randomized _challenge data_).
2. The second packet should be the client's _response_ (containing the client's ID and a signature of the _challenge data_).

Challenge Payload:
```
Bytes          | Field
----------------------
0:1            | Key Size (key_size, max 65KiB) 
2:2+key_size   | Server public key
2+key_size:N   | Challenge data (challenge_data)
```

_Challenge data_ should be _settings.challenge_size_ bytes (default 2048) of randomized data. This is done to prevent caching of response data.

Response Payload:
```
Bytes | Field
-------------
0:16  | Client ID (client_id)
16:N  | Signature
```

#### C2C, C2S, S2C, S2S
All message types are are either client-to-client (c2c), client-to-server (c2s), server-to-client (s2c) or.

Prior to message processing, the _payload data_ must be decrypted into _message data_ using the _server private key_ or _client private key_.

The first byte of the _message data_ are reserved to indicate the format of the message:
- 0: c2c
- 1: c2s or s2c
- 2: s2s
- 3-7: Reserved for future use

```
Bytes  | Field
-------------
0[0:3] | Message format (0=Client-Client, 1=Server-Client or Client-Server, 2=Server-Server)
0[4:7] | Message type (0 for C2C)
```

##### Scoping
Crucially, C2C is the only type of message that can be received on both the socket and the client's message queue on the server. C2S and S2C can only be received on the socket, while S2S can only be received via the client's message queue.

Any message deviating from this convention must be disacrded.

##### Client-to-Client (C2C)
C2C messages are meant to be routed between clients, and so the majority of the _message data_ is reserved for client-defined data.

The first 16 bytes indicate the recipient client ID.

```
Bytes | Field
-------------
1:17  | Recipient ID
17:N  | C2C data
```

##### Client-to-Server (C2S)
C2S messages are used by the client to communicate with the server _client handler_ on the server.

The most fundamental C2S messages are 'HEARTBEAT', 'STOP' and 'CONFIG':
- HEARTBEAT: A signal sent periodically to inform the handler that the client is still alive.
- STOP: Used by either end of the connection to indicate that the connection will be closed.
- CONFIG: Used by the server to provide upddated connection settings to the client.

```
Bytes | Field
-------------
1:5   | unix Timestamp (seconds)
5:N   | Message type-specific data
```

Message Types:
```
Number | Message Type | Notes
------------------------------
0      | HEARTBEAT    | Client is alive and wishes to keep the connection open for another _settings.heartbeat_interval_.
1      | CONFIG       | Usd by server to inform client about updates to connection settings.
15     | STOP         | Used by client or server to indicate that the connection will be closed.
```

HEARTBEAT message:
```
Bytes | Field
-------------
1:5   | Unix timestamp (seconds)
```

CONFIG message:
```
Bytes | Field
-------------
1:5   | Unix timestamp (seconds)
5:N   | JSON-formated connection settigs (expected to be UTF-8)
```

STOP message:
```
Bytes | Field
-------------
1:5   | Unix timestamp (seconds)
5:N   | Reason message (UTF-8 encoded string)
```

## Appendix A: Settings
- **challenge_size**: Size in bytes of the randomized _challenge data_ sent to clients as part of the authentication challenge.
- **heartbeat_timout**: Time of inactivity (in seconds) that the _client handler_ should wait before assuming a client is dead.
- **heartbeat_interval**: Time of inactivity before the client should send a _HEARTBEAT_ message.