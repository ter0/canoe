# Canoe 🛶

[![Documentation Status](https://readthedocs.org/projects/canoe/badge/?version=latest)](http://canoe.readthedocs.io/en/latest/?badge=latest) [![Build Status](https://travis-ci.org/ter0/canoe.svg?branch=master)](https://travis-ci.org/ter0/canoe) [![Coverage Status](https://coveralls.io/repos/github/ter0/canoe/badge.svg)](https://coveralls.io/github/ter0/canoe)

Canoe is a Python implementation of the Raft consensus algorithm. It currently utilises zerorpc for making RPC calls, and msgpack for persistence.

# Todo

 - [ ] Get that test coverage up.
 - [ ] Log replication. A lot of the log replication work is already implemented as a by product of leader election.
 - [ ] Log compaction.
 - [ ] Snapshots.
 - [ ] Remove the dependency on zerorpc. zerorpc is a fantastic tool but some of its features, such as message queueing and heartbeats, are not necessary for an implementation of Raft. The plan is to remove this hard dependency and implement a pluggable RPC layer. First pass should just be TCP sockets.
 - [ ] Build a proof of concept key value store on top of Canoe. This will be a separate project, but will provide a nice, simple example of using Canoe to build a distributed system.
 - [ ] Write an intro guide to using Canoe. The [Read The Docs](http://canoe.readthedocs.io/en/latest) page is currently just the API docs.
