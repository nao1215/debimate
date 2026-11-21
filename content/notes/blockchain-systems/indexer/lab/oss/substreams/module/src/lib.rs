use substreams::errors::Error;
use substreams::Hex;
use substreams_database_change::pb::database::DatabaseChanges;
use substreams_database_change::tables::Tables;
use substreams_ethereum::pb::eth::v2 as eth;

// Token deployed by Anvil account 0 with nonce 0.
const TOKEN: [u8; 20] = hex_literal(b"5fbdb2315678afecb367f032d93f642f64180aa3");
// keccak256("Transfer(address,address,uint256)")
const TRANSFER_TOPIC: [u8; 32] = hex_literal32(b"ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef");

const fn nib(c: u8) -> u8 {
    match c {
        b'0'..=b'9' => c - b'0',
        b'a'..=b'f' => c - b'a' + 10,
        _ => panic!("bad hex"),
    }
}
const fn hex_literal(s: &[u8; 40]) -> [u8; 20] {
    let mut out = [0u8; 20];
    let mut i = 0;
    while i < 20 {
        out[i] = nib(s[2 * i]) << 4 | nib(s[2 * i + 1]);
        i += 1;
    }
    out
}
const fn hex_literal32(s: &[u8; 64]) -> [u8; 32] {
    let mut out = [0u8; 32];
    let mut i = 0;
    while i < 32 {
        out[i] = nib(s[2 * i]) << 4 | nib(s[2 * i + 1]);
        i += 1;
    }
    out
}

fn u256_dec(b: &[u8]) -> String {
    // value fits in u128 in this experiment
    let mut v: u128 = 0;
    for x in &b[b.len().saturating_sub(16)..] {
        v = (v << 8) | (*x as u128);
    }
    v.to_string()
}

#[substreams::handlers::map]
fn db_out(blk: eth::Block) -> Result<DatabaseChanges, Error> {
    let mut tables = Tables::new();
    let block_hash = Hex(&blk.hash).to_string();
    for log in blk.logs() {
        if log.address() != TOKEN {
            continue;
        }
        let topics = log.topics();
        if topics.len() != 3 || topics[0].as_slice() != TRANSFER_TOPIC {
            continue;
        }
        let id = format!("{}-{}", Hex(&log.receipt.transaction.hash), log.index());
        tables
            .create_row("transfers", id)
            .set("block_num", blk.number)
            .set("block_hash", &block_hash)
            .set("from_addr", Hex(&topics[1][12..]).to_string())
            .set("to_addr", Hex(&topics[2][12..]).to_string())
            .set("amount", u256_dec(log.data()));
    }
    Ok(tables.to_database_changes())
}
