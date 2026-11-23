use unicode_width::UnicodeWidthStr;

fn main() {
    for (label, s) in [("ｶ", "\u{FF76}"), ("ﾞ", "\u{FF9E}"), ("ｶﾞ", "\u{FF76}\u{FF9E}"), ("①", "\u{2460}"), ("tab", "\t")] {
        println!("{label}\twidth={}\twidth_cjk={}", s.width(), s.width_cjk());
    }
}
