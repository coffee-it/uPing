# µPing (MicroPing) for MicroPython (Unix version)
# License: MIT
# copyright (c) 2020 coffee-it

# recommendations from
# https://forum.micropython.org/viewtopic.php?t=5287

# µPing (MicroPing) for MicroPython
# copyright (c) 2018 Shawwwn <shawwwn1@gmail.com>
# License: MIT

# Internet Checksum Algorithm
# Author: Olav Morken
# https://github.com/olavmrk/python-ping/blob/master/ping.py
# @data: bytes

import utime
import uselect
import uctypes
import usocket
import ustruct
import urandom
import micropython
urandom.seed(utime.ticks_us())

class Ping():
    """
    Create the ping calculating object exemplar
    """
    def __init__(self, HOST, SOURCE=None, COUNT=4, INTERVAL=1000, SIZE=64, TIMEOUT=5000, quiet=False):
        self.HOST     = HOST
        self.COUNT    = COUNT
        self.TIMEOUT  = TIMEOUT
        self.INTERVAL = INTERVAL
        self.SIZE     = SIZE
        self.quiet    = quiet

        # prepare packet
        assert SIZE >= 16, "pkt size too small"
        self._PKT = b'Q'*SIZE
        self.PKT_DESC = {
            "type": uctypes.UINT8 | 0,
            "code": uctypes.UINT8 | 1,
            "checksum": uctypes.UINT16 | 2,
            "id": uctypes.UINT16 | 4,
            "seq": uctypes.INT16 | 6,
            "timestamp": uctypes.UINT64 | 8,
        } # packet header descriptor
        h = uctypes.struct(uctypes.addressof(self._PKT), self.PKT_DESC, uctypes.BIG_ENDIAN)
        h.type = 8 # ICMP_ECHO_REQUEST
        h.code = 0
        h.checksum = 0
        h.id = urandom.getrandbits(16)
        h.seq = 1
        self.h = h

        # init socket
        sock = usocket.socket(usocket.AF_INET, usocket.SOCK_RAW, 1)
        if SOURCE:
            src_addr = usocket.getaddrinfo(SOURCE, 1)[0][-1] # ip address
            sock.bind(src_addr)
        sock.setblocking(0)
        sock.settimeout(TIMEOUT/1000)
        addresses = usocket.getaddrinfo(HOST, 1) # [0][-1] # list of ip addresses
        assert addresses, "Can not take the IP address of host"
        self.CLIENT_IP = None
        for addr in addresses:
            try:
                sock.connect(addr[-1])
                self.CLIENT_IP = usocket.inet_ntop(usocket.AF_INET, addr[-1][4:8])
            except:
                continue
        assert self.CLIENT_IP, "Connection failed"
        self.sock = sock

        # [ COUNTERS ]
        self.seq_num = 1 # Next sequence number
        self.transmitted = 0
        self.received = 0
        self.seqs = None

    def start(self):
        """
        Starting a ping cycle with the specified settings (like a interval, count e.t.c.)
        """
        t = self.INTERVAL
        finish = False

        # [ Rtt metrics ]
        pongs = []
        min_rtt, max_rtt = None, None
        # [ Start over ]
        self.seq_num = 1
        self.transmitted = 0
        self.received = 0
        not self.quiet and print("PING %s (%s): %u data bytes" % (self.HOST, self.CLIENT_IP, len(self._PKT)))

        if self.seqs:
            self.seqs.extend(list(range(self.seq_num, self.COUNT + 1))) # [seq_num, seq_num + 1, ...., seq_num + n])
        else:
            self.seqs = list(range(self.seq_num, self.COUNT + 1)) # [1,2,...,count]

        # Здесь нужно подвязаться на реальное время
        while self.seq_num <= self.seq_num + self.COUNT:
            if t >= self.INTERVAL:
                pong = self.ping()
                t = 0
                rtt = pong[1]
                if rtt:
                    pongs.append(rtt)
                    if not min_rtt or rtt <= min_rtt: min_rtt = round(rtt, 3)
                    if not max_rtt or rtt >= max_rtt: max_rtt = round(rtt, 3)
                if len(self.seqs) == 0:
                    finish = True
            if finish:
                break

            utime.sleep_ms(1)
            t += 1

        losses = round((self.transmitted - self.received) / self.transmitted) * 100
        avg_rtt = round(sum(pongs) / len(pongs), 3) if pongs else None
        from ucollections import namedtuple
        _result = namedtuple("result", ("tx", "rx", "losses", "min", "avg", "max"))
        result = _result(self.transmitted, self.received, losses, min_rtt, avg_rtt, max_rtt)
        if not self.quiet:
            print(r'%u packets transmitted, %u packets received, %u packet loss' % (self.transmitted, self.received, losses))
            if avg_rtt: print(r'round-trip min/avg/max = %r/%r/%r ms' % (min_rtt, avg_rtt, max_rtt))
        else:
            return result

    def ping(self):
        """
        Send ping manually.
        Returns sequense number(int), round-trip time (ms, float), ttl
        """
        sock = self.sock
        if not self.seqs:
            self.seqs = []
            self.seqs.append(self.seq_num)
        seq, t_elasped, ttl = None, None, None

        # header
        h = self.h
        h.checksum = 0
        h.seq = self.seq_num
        h.timestamp = utime.ticks_us()
        h.checksum = self.checksum(self._PKT)

        try:
            # send packet
            if sock.send(self._PKT) == self.SIZE:
                self.transmitted += 1
            else:
                self.seqs.remove(self.seq_num)
            self.seq_num += 1

            # recv packet
            while 1:
                resp = sock.recv(self.SIZE + 20) # ICMP header and payload + IP header
                resp_mv = memoryview(resp)
                h2 = uctypes.struct(uctypes.addressof(resp_mv[20:]), self.PKT_DESC, uctypes.BIG_ENDIAN)
                seq = h2.seq
                if h2.type==0 and h2.id==h.id and (seq in self.seqs): # 0: ICMP_ECHO_REPLY
                    t_elasped = (utime.ticks_us()-h2.timestamp) / 1000
                    self.seqs.remove(seq)
                    if h2.checksum == self.checksum(resp[24:]): # except IP header and a part of ICMP header (type, code, checksum)
                        ttl = ustruct.unpack('!B', resp_mv[8:9])[0] # time-to-live
                        self.received += 1
                        not self.quiet and print("%u bytes from %s: icmp_seq=%u, ttl=%u, time=%f ms" % (len(resp[12:]), self.CLIENT_IP, seq, ttl, t_elasped))
                        break
                    else:
                        not self.quiet and print("Payload checksum doesnt match")
                        t_elasped = None
                        break

        except Exception as identifier:
            import errno
            if identifier.args[0] == errno.EPIPE:
                print("Client connection unexpectedly closed")
                pass
            elif identifier.args[0] == errno.EBADF:
                print("Bad file descriptor.")
                pass
            else:
                raise identifier
        return (seq, t_elasped, ttl)

    def checksum(self, data):
        if len(data) & 0x1: # Odd number of bytes
            data += b'\0'
        cs = 0
        for pos in range(0, len(data), 2):
            b1 = data[pos]
            b2 = data[pos + 1]
            cs += (b1 << 8) + b2
        while cs >= 0x10000:
            cs = (cs & 0xffff) + (cs >> 16)
        cs = ~cs & 0xffff
        return cs

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.sock.close()
