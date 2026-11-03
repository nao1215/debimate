use methods::{FACTOR_GUEST_ELF, FACTOR_GUEST_ID};
use risc0_zkvm::{ExecutorEnv, InnerReceipt, Prover, ProverOpts};
use risc0_zkvm::LocalProver;

fn main() {
    // Tiny, intentionally guessable teaching inputs, not a privacy demonstration.
    let env = ExecutorEnv::builder()
        .write(&(17_u32, 23_u32)).unwrap()
        .build().unwrap();
    let start = std::time::Instant::now();
    // Explicit local CPU prover: no remote proving service or dev-mode fallback.
    let info = LocalProver::new("local")
        .prove_with_opts(env, FACTOR_GUEST_ELF, &ProverOpts::succinct()).unwrap();
    let receipt = info.receipt;
    assert!(!matches!(receipt.inner, InnerReceipt::Fake(_)));
    receipt.verify(FACTOR_GUEST_ID).unwrap();
    let product: u32 = receipt.journal.decode().unwrap();
    assert_eq!(product, 391);
    println!("receipt_kind=succinct; dev_mode=disabled");
    println!("verify_expected_image=PASS; public_product={product}");

    let mut tampered = receipt.clone();
    tampered.journal.bytes[0] ^= 1;
    assert!(tampered.verify(FACTOR_GUEST_ID).is_err());
    println!("tampered_journal=REJECTED");

    let mut wrong_id = FACTOR_GUEST_ID;
    wrong_id[0] ^= 1;
    assert!(receipt.verify(wrong_id).is_err());
    println!("wrong_image_id=REJECTED");
    println!("elapsed_seconds={:.2}", start.elapsed().as_secs_f64());
    println!("Assertions: PASS");
}
