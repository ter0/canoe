from structlog import get_logger

log = get_logger()


class RaftTerm:
    """A representation of a term as defined in Raft.

    Encapsulates the concept of a term in the Raft consensus algorithm.
    Ensures that the term is monotonically increasing, and resets voting
    information when the term increases.

    Attributes:
        voted_for (str): the candidate_id of the peer that received a vote this term
        votes (set(str)): set of candidate_id that have granted a vote this term
    """

    def __init__(self):
        self._current_term = 0
        self.voted_for = None
        self.votes = set()

    @property
    def current_term(self):
        """int: the current term number

        The term *must* be monotonically increasing.

        Setting the term to a value greater than the existing value will reset the granted vote
        and received votes values.

        Raises:
            AttributeError: If current_term is set to a value lower than it's existing value.
                i.e. if it does not increase monotonically.
        """
        return self._current_term

    @current_term.setter
    def current_term(self, current_term: int):
        log.info("set_current_term", old_term=self._current_term, new_term=current_term)
        # ensure current_term is monotonically increasing
        if current_term < self._current_term:
            raise AttributeError("current_term must be monotonically increasing")
        elif current_term > self._current_term:
            # if term has increased, reset votes issued and received
            self._current_term = current_term
            self.voted_for = None
            self.votes = set()
