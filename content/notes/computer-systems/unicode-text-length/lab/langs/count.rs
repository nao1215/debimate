fn main() {
    let s = "\u{1F468}\u{200D}\u{1F469}\u{200D}\u{1F467}"; // 👨‍👩‍👧
    println!("rust s.len()                = {}", s.len());
    println!("rust s.chars().count()      = {}", s.chars().count());
    println!("rust s.encode_utf16().count() = {}", s.encode_utf16().count());
}
