import uuid
from datetime import datetime
import enum

class BackboneMessageFormat(enum.IntEnum):
    C2C = 0
    C2S = 1
    S2S = 2

class BackboneMessageType(enum.IntEnum):
    pass

class BackboneC2SType(BackboneMessageType):
    HEARTBEAT = 0   # Used by client to let the handler know that it is alive.
    CONFIG    = 1   # Used by handler to inform client about connection configuration changes.
    STOP      = 15  # Used by client & handler to inform the other end to close the connection.

class BackboneS2SType(BackboneMessageType):
    DONE  = 14
    STOP  = 15

# Base class for all Backbone messages:
class BackboneMessage:
    def __init__(self, format:BackboneMessageFormat, type:BackboneMessageType) -> None:
        if format not in BackboneMessageFormat:
            raise ValueError(f"Invalid Backbone message format: {format}")

        self.format = format
        self.type = type
    
    def to_bytes(self):
        msg_typing = ((self.format << 4) + self.type).to_bytes(1)
        return msg_typing
    
    def  __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BackboneMessage):
            return False
        return __o.format == self.format and __o.type == self.type
    
    @staticmethod
    def from_bytes(frame:bytes):
        t =  frame[0] & 0b00001111
        f = (frame[0] & 0b11110000) >> 4

        try:
            f = BackboneMessageFormat(f)
            match f:
                case BackboneMessageFormat.C2C:
                    # C2C messages don't have separate types, so this should be 0.
                    if t != 0: return None # This is not a valid message frame
                    recipient_id = uuid.UUID(bytes=frame[1:17])
                    payload      = frame[17:] if 17 < len(frame) else None
                    return BackboneMessageC2C(recipient_id, payload)

                case BackboneMessageFormat.C2S:
                    t = BackboneC2SType(t)
                    timestamp = datetime.fromtimestamp(int.from_bytes(frame[1:5]))
                    return BackboneMessageC2S(t, timestamp)

                case BackboneMessageFormat.S2S:
                    t = BackboneS2SType(t)
                    timestamp = datetime.fromtimestamp(int.from_bytes(frame[1:5]))
                    return BackboneMessageS2S(t, timestamp)
                
        except ValueError as e:
            print(e)
            return None


class BackboneMessageC2C(BackboneMessage):
    def __init__(self, recipient:uuid.UUID, payload:bytes) -> None:
        super().__init__(BackboneMessageFormat.C2C, 0)
        self.recipient = recipient
        self.payload   = payload
    
    def to_bytes(self):
        frame = super().to_bytes()
        return frame + self.recipient.bytes + self.payload
    
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BackboneMessageC2C):
            return False
            
        return super().__eq__(__o) and __o.recipient == self.recipient and __o.payload == self.payload
        

class BackboneMessageC2S(BackboneMessage):
    def __init__(self, type:BackboneC2SType, timestamp:datetime=None, payload:bytes=None) -> None:
        if type not in BackboneC2SType:
            raise ValueError(f"Invalid Backbone C2S type: {type}")
        super().__init__(BackboneMessageFormat.C2S, type)
        if timestamp == None:
            timestamp = datetime.now()
        
        self.timestamp = datetime.fromtimestamp(int(timestamp.timestamp()))
        self.payload   = payload
    
    def to_bytes(self):
        frame = super().to_bytes()
        payload = self.payload if self.payload != None else b''
        return frame + int(self.timestamp.timestamp()).to_bytes(4) + payload

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BackboneMessageC2S):
            return False
            
        return super().__eq__(__o) and __o.timestamp == self.timestamp and __o.payload == self.payload


class BackboneMessageS2S(BackboneMessage):
    def __init__(self, type:BackboneS2SType, timestamp:datetime=None, payload:bytes=None) -> None:
        if type not in BackboneS2SType:
            raise ValueError(f"Invalid Backbone S2S type: {type}")
        super().__init__(BackboneMessageFormat.S2S, type)
        if timestamp == None:
            timestamp = datetime.now()
        
        self.timestamp = datetime.fromtimestamp(int(timestamp.timestamp()))
        self.payload   = payload

    def to_bytes(self):
        frame = super().to_bytes()
        payload = self.payload if self.payload != None else b''
        return frame + int(self.timestamp.timestamp()).to_bytes(4) + payload
    
    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, BackboneMessageS2S):
            return False
            
        return super().__eq__(__o) and __o.timestamp == self.timestamp and __o.payload == self.payload
