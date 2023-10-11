# Demonstration REST adapter

This adapter is designed for demonstration of the zone-server capability.


## Known issues

- [ ] If a /sync/ request is made while the zone-server is set to IDLE, then /zone_set/ requests no longer change the zone set index. This may be an issue with the multiprocessing queues?