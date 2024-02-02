"""
BufferInfo -- describe a sysv shared memory buffer
"""
from carp.serializer import Serializable


class BufferInfo(Serializable):
    def __init__(self, *, buf_id, size, channels, rate, offset=0):
        self.buf_id = buf_id
        self.size = int(size)
        self.channels = int(channels)
        self.rate = int(rate)
        self.offset = int(offset)
        super().__init__()

    def to_dict(self):
        return dict(
            buf_id=self.buf_id,
            size=self.size,
            channels=self.channels,
            rate=self.rate,
            offset=self.offset
        )

    def __repr__(self):
        return f"<buf_id={self.buf_id}, channels={self.channels}, size={self.size}, rate={self.rate}>"
