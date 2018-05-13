
class BufferInfo(object):
    def __init__(self, buf_id, size, channels, rate, offset=0):
        self.buf_id = buf_id
        self.size = size
        self.channels = channels
        self.rate = rate
        self.offset = offset

    def __repr__(self):
        return "<buf_id=%s, channels=%d, size=%d, rate=%d>" % (self.buf_id, self.channels, self.size, self.rate)


