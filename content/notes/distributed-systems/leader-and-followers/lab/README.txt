Raft leader election simulation (election.py)

  python3 election.py > election_output.txt   # standard library only, about 20 s, seed fixed
  python3 ../figures.py                       # regenerates images/leader-and-followers_election_timeout.svg

Assumptions (5 servers, message delay 2-8 ms, equal logs) are written at the
top of election.py. The shape follows Figure 16 of the Raft paper; the numbers
are not a reproduction of it.
