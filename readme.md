# Busman

Python ports of various Haskell ideas from the past:
* https://github.com/voneiden/ubootp
* https://github.com/voneiden/busbroker

This monorepo (I hate monorepos, but here we are) implements three projects:

* Busman - the django backend for storing and managing all dynamic data
  * MAC to IP mappings for ubootp
  * Route mappings for Busrouter
* Ubootp proxy - Broadcast/Multicast listener with a very simple protocol. 
  Returns IP configuration for matching MAC addresses.
* Busrouter - A very lightweight TCP pubsub server/broker. Very fast.