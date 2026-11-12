pragma circom 2.1.0;
// x が 0 なら out = 1、0 でなければ out = 0
template IsZero() {
    signal input x;
    signal output out;
    signal inv;
    inv <-- x != 0 ? 1 / x : 0;   // 証明する人が計算する値（制約にならない）
    out <== 1 - x * inv;          // 制約 1
}
component main {public [x]} = IsZero();
