## µPing (MicroPing) for MicroPython (Unix version)

Run with default settings
```python
import uping
pinger = uping.Ping('example.org')
pinger.start()
```
```
PING example.org (93.184.216.34): 56 data bytes
64 bytes from 93.184.216.34: seq=0 ttl=54 time=106.261 ms
64 bytes from 93.184.216.34: seq=1 ttl=54 time=106.221 ms
64 bytes from 93.184.216.34: seq=2 ttl=54 time=106.421 ms
64 bytes from 93.184.216.34: seq=3 ttl=54 time=107.521 ms
4 packets transmitted, 4 packets received, 0 packet loss
round-trip min/avg/max = 106.221/106.606/107.521 ms
```
---
### Arguments:
Required
- HOST     (FQDN or IP address)

Optional
- SOURCE   (default: None, ip address)
- COUNT    (default: 4, integer)
- INTERVAL (default: 1000, ms)
- SIZE     (default: 64, bytes)
- TIMEOUT  (default: 5000, ms)
- quiet    (default: False, bool)
---

### Class methods
#### Ping.start()
> Starting ping loop with given parameters. Always starts at the first sequence number.
> If quiet then returns tupple with ping results
> result(tx=4, rx=4, losses=0, min=106.221, avg=106.606, max=107.521)
> tx - transmitted
> rx - received
> losses - percentage of packets that be lost

#### Ping.ping()
> Sending just a one packet. Keeps and increment current sequence number.
> Returns sequense number(int), round-trip time (ms, float), ttl(int)
```python
import uping
pinger = uping.Ping('example.org')
# Some awesome code
pong = pinger.ping()
print(pong)
```
> (5, 106.521, 54)