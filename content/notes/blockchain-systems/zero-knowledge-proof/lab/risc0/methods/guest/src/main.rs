#![no_main]
#![no_std]

risc0_zkvm::guest::entry!(main);

fn main() {
    let (a, b): (u32, u32) = risc0_zkvm::guest::env::read();
    assert!(a > 1 && b > 1);
    let product = a.checked_mul(b).expect("u32 overflow");
    risc0_zkvm::guest::env::commit(&product);
}
