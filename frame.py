def read(conn):
    l_b = conn.recv(2)
    l   = int.from_bytes(l_b)
    return conn.recv(l)

def send(conn, msg):
    l = len(msg)
    l_b = l.to_bytes(2)
    conn.sendall(l_b)
    conn.sendall(msg)
