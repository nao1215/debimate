RISC Zero local proof experiment

Requirements tested:
- Linux x86_64, host rustc 1.98.0
- rzup 0.6.0; RISC Zero Rust toolchain 1.97.0 (rustup name: risc0)
- risc0-zkvm and risc0-build 3.0.6; transitive versions in both Cargo.lock files
- C/C++ compiler and normal Rust native build prerequisites
- CPU proving, no CUDA feature or external proving service

Install rzup following https://dev.risczero.com/zkvm/quickstart and run:
  rzup install rust 1.97.0
Then, from this lab directory:
  cargo run --release --locked -p zk-note

If the toolchain lives outside ~/.risc0, set RISC0_HOME to its rzup directory.
You can set CARGO_TARGET_DIR to keep build artifacts outside the Page Bundle.
The first build downloads dependencies and builds the native prover.
The official docs recommend at least 16 GB RAM for local proving.
Do not set RISC0_DEV_MODE: disable-dev-mode is deliberately enabled.

The guest checks a,b > 1, checked u32 multiplication, and commits the product.
The host uses teaching inputs 17 and 23. They are deliberately public in the
source and easily recoverable from 391: this is not a secret-storage example.
The host explicitly invokes LocalProver with succinct receipts (recursive compression), rejects Fake,
checks receipt.verify against the compiled expected image ID and checks 391.
It also checks rejection of a tampered journal and a changed expected image ID.

output/summary.txt is actual stdout from a successful local execution.
The succinct form avoids the execution-length leakage documented for proofs
not passed through the recursion prover. See:
https://dev.risczero.com/api/security-model#zero-knowledge-proving
Elapsed time includes proving, verification and negative checks, not compilation;
it is one observation on this machine, not a benchmark or performance promise.
