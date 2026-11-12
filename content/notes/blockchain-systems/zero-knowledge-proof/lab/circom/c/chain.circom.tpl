pragma circom 2.1.0;
// 秘密の x から y = (…((x^2 + 1)^2 + 1)…) を N 回計算したことを証明する
template Chain(N) {
    signal input x;      // 秘密
    signal output y;     // 公開
    signal t[N + 1];
    t[0] <== x;
    for (var i = 0; i < N; i++) {
        t[i + 1] <== t[i] * t[i] + 1;   // 1 回ごとに制約 1 つ
    }
    y <== t[N];
}
component main = Chain(__N__);
