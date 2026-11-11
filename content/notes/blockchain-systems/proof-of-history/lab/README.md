# Proof of History lab

`poh.go` builds a SHA-256 hash chain in the style of Solana's Proof of History,
mixes three events into it, and verifies it with 1 to 32 goroutines.
It uses only the Go standard library and does not access the network.

```sh
go run poh.go          # 7 runs per measurement (Go 1.22 or later)
go run poh.go -runs 3  # quicker
```

`output.txt` is the run shown in the note (2026-11-10, Go 1.26.4,
AMD Ryzen AI MAX+ 395, cpufreq governor powersave, other jobs running).

What a rerun reproduces exactly:

- the last hash of the chain (`0751853592b4...`)
- the first bad entry after swapping events (100) and after shortening `NumHashes` (10)
- the number of hashes to redo after the swap (15,949,825, from the mix in entry 100
  to the last entry) and per 400 ms-era slot (4,000,000)

Timings depend on the CPU and on its load. Each measurement is the median of
`-runs` repetitions after one warm-up run, with the min-max range.

`../figures.py` reads `output.txt` to draw `images/proof-of-history_verify.webp`.
