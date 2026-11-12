pragma circom 2.1.0;
// x が 0 なら out = 1、0 でなければ out = 0
template IsZero() {
    signal input x;
    signal output out;
    signal inv;
    inv <-- 0;                    // 偽の証明者は 0 を入れる
    out <== 1 - x * inv;          // 制約 1
    x * out === 0;                // 制約 2
}
component main {public [x]} = IsZero();
