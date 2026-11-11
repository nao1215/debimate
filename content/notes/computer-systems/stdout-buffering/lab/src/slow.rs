use std::{thread, time::Duration};

fn main() {
    for i in 1..=5 {
        println!("line {i}");
        thread::sleep(Duration::from_millis(500));
    }
}
