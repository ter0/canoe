import concurrent.futures
import logging
import math
import os
import random
import sys
import uuid
from enum import IntEnum
from typing import Dict, List

import msgpack
import zerorpc
from gevent import monkey
from structlog import get_logger

from .restartable_timer import RestartableTimer
from .term import RaftTerm

monkey.patch_all()
log = get_logger()


class RaftElectionState(IntEnum):
    """The possible election states a machine can be in.

    Subclassed from ``IntEnum`` to allow easy serialization in msgpack.

    """
    FOLLOWER = 0
    CANDIDATE = 1
    LEADER = 2


class Raft:
    """A peer in a Raft cluster.

    Args:
        address: A string of the format ``127.0.0.1:5254``, that this instance will listen on
        peers: A list of strings of peer addresses
        election_timeout_min: The minimum time (in seconds) between election timeouts
        election_timeout_min: The maximum time allowed for the election timeout
        
    Attributes:
        state_cache_path: Path to the state cache
        term: The ``RaftTerm`` object for this peer
        candidate_id: A unique identifier for this instance
        log: The replicated log
        state: The current state of this instance
        peers: A list of peers in the cluster
        address: The bind address
        election_timer: The ``RestartableTimer`` used for election timeouts
        heartbeat_timer: The ``RestartableTimer`` used for heartbeat timeouts
        commit_index:
        last_applied:
        next_index:
        match_index:

    """
    def __init__(self, address, peers, election_timeout_min=5, election_timeout_max=10):
        base_cache_dir = os.getenv('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache')
        self.state_cache_path = os.path.join(base_cache_dir, 'state')
        self.term = RaftTerm()
        # TODO: candidate_id should be a uuid.uuid4(), but
        # using the bind address makes for easier testing on
        # a single machine
        self.candidate_id = address
        self.log = []
        self.state = RaftElectionState.FOLLOWER

        self.peers = [zerorpc.Client()] * len(peers)
        for index, peer in enumerate(self.peers):
            peer.connect('tcp://' + peers[index])
        self.address = address
        self.election_timer = RestartableTimer(random.uniform(
            election_timeout_min, election_timeout_max), self.election_timeout)
        self.heartbeat_timer = RestartableTimer(election_timeout_min / 2, self.heartbeat_timeout)
        self.commit_index = 0
        self.last_applied = 0

        self.next_index = []
        self.match_index = []

    def save_persistent_state(self):
        with open(self.state_cache_path, 'w+b') as state_file:
            msgpack.pack({
                'state': self.state,
                'candidate_id': self.candidate_id,
                'current_term': self.term.current_term,
                'voted_for': self.term.voted_for,
                'log': self.log
            }, state_file, use_bin_type=True)

    def load_persistent_state(self):
        state = None
        try:
            with open(self.state_cache_path) as state_file:
                state = msgpack.unpack(state_file, use_bin_type=True)
        except FileNotFoundError:
            # if the file doesn't exist ignore it, and we'll act like a new server
            pass
        return state

    def heartbeat_timeout(self):
        log.info('heartbeat_timeout', timeout=self.heartbeat_timer.interval)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.peers)) as executor:
            heartbeats = [executor.submit(peer.append_entries_rpc, self.term.current_term,
                                          self.candidate_id, 0, 0, []) for peer in self.peers]
            for future in concurrent.futures.as_completed(heartbeats):
                response = future.result()
                if response['term'] > self.term.current_term:
                    self.term.current_term = response['term']
                    self.become_follower()
        self.heartbeat_timer.restart()

    def election_timeout(self):
        log.info('election_timeout', timeout=self.election_timer.interval)
        self.become_candidate()

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.peers)) as executor:
            vote_requests = [executor.submit(peer.request_vote_rpc, self.term.current_term,
                                             self.candidate_id, 0, 0) for peer in self.peers]
            for future in concurrent.futures.as_completed(vote_requests):
                vote = future.result()
                if vote['vote_granted']:
                    log.info('vote_received', candidate_id=vote['candidate_id'], term=self.term.current_term)
                    self.term.votes.add(vote['candidate_id'])
                elif vote['term'] > self.term.current_term:
                    self.term.current_term = vote['term']
                    self.become_follower()
        majority = (len(self.peers) // 2) + 1
        log.info('election_result', votes_received=self.term.votes, majority=majority, term=self.term.current_term)
        if len(self.term.votes) >= majority:
            self.become_leader()

    def start(self):
        log.info('start', candidate_id=self.candidate_id)
        server = zerorpc.Server(self)
        server.bind('tcp://{}'.format(self.address))
        self.election_timer.start()
        server.run()

    def become_leader(self):
        log.info('become_leader')
        self.state = RaftElectionState.LEADER
        self.election_timer.stop()
        self.heartbeat_timeout()
        self.heartbeat_timer.start()

    def become_candidate(self):
        log.info('become_candidate')
        self.state = RaftElectionState.CANDIDATE
        self.term.current_term += 1

        log.info('vote_for_self')
        self.term.votes.add(self.candidate_id)
        self.election_timer.restart()

    def become_follower(self):
        log.info('become_follower')
        self.state = RaftElectionState.CANDIDATE
        self.election_timer.restart()

    def append_entries_rpc(self, term: int, leader_id: str, prev_log_index: int, prev_log_term: int, entries: List) -> Dict:
        # 1.  Reply false if term < currentTerm (§5.1)
        # 2.  Reply false if log doesn’t contain an entry at prevLogIndex
        #     whose term matches prevLogTerm (§5.3)
        # 3.  If an existing entry conflicts with a new one (same index
        #     but different terms), delete the existing entry and all that
        #     follow it (§5.3)
        # 4.  Append any new entries not already in the log
        # 5.  If leaderCommit > commitIndex, set commitIndex =
        #     min(leaderCommit, index of last new entry)
        log.info('append_entries_rpc', term=term, leader_id=leader_id,
                 prev_log_index=prev_log_index, prev_log_term=prev_log_term, entries=entries)
        self.save_persistent_state()

        if term < self.term.current_term:
            return {
                'term': self.term.current_term,
                'success': False
            }
        self.term.current_term = term

        try:
            if self.log and self.log[prev_log_index].term != prev_log_term:
                return {
                    'term': self.term.current_term,
                    'success': False
                }
        except IndexError:
            return {
                'term': self.term.current_term,
                'success': False
            }


        self.become_follower()

        return {
            'term': self.term.current_term,
            'success': True
        }

    def request_vote_rpc(self, term: int, candidate_id: str, last_log_index: int, last_log_term: int) -> Dict:
        # 1.  Reply false if term < currentTerm (§5.1)
        # 2.  If votedFor is null or candidateId, and candidate’s log is at
        #    least as up-to-date as receiver’s log, grant vote (§5.2, §5.4)
        log.info('request_vote_rpc', term=term, candidate_id=candidate_id,
                 last_log_index=last_log_index, last_log_term=last_log_term)
        self.save_persistent_state()

        if term < self.term.current_term:
            return {
                'term': self.term.current_term,
                'vote_granted': False
            }

        if (self.term.voted_for is None or self.term.voted_for == candidate_id) and last_log_index >= len(self.log):
            log.info('vote_granted', candidate_id=candidate_id)
            self.term.voted_for = candidate_id
            return {
                'term': self.term.current_term,
                'vote_granted': True,
                'candidate_id': self.candidate_id
            }

        return {
            'term': self.term.current_term,
            'vote_granted': False
        }


if __name__ == '__main__':
    Raft(address=sys.argv[1], peers=[sys.argv[2], sys.argv[3]]).start()
