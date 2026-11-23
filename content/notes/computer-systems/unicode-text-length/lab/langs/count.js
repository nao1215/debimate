const s = "\u{1F468}\u200D\u{1F469}\u200D\u{1F467}"; // 👨‍👩‍👧
console.log("js s.length                  =", s.length);
console.log("js [...s].length             =", [...s].length);
const seg = new Intl.Segmenter("ja", { granularity: "grapheme" });
console.log("js Intl.Segmenter            =", [...seg.segment(s)].length);
