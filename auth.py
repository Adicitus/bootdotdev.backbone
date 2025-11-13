import frame

# Super-basic challenge-response setup, to be replaced.
expected = {
    "challenge": { "len": 5, "val": b'hello' },
    "response":  { "val": b'world', "len": 5 }
}

def challenge(clientsock):
    # This should be replaced with a signature validation.
    frame.send(clientsock, expected["challenge"]["val"])
    response = frame.read(clientsock)
    if response == expected["response"]["val"]:
        msg = b'Connection authenticated!'
        frame.send(clientsock, msg)
    else:
        clientsock.close()