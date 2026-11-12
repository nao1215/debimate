// SPDX-License-Identifier: MIT
// 実験用のトークン 4 種と、預け入れを記帳する Vault。ローカルの Anvil だけで使う。
pragma solidity 0.8.28;

// EIP-20 の書き方どおりのトークン。失敗は revert し、成功は true を返す。
contract StandardToken {
    string public name;
    string public symbol;
    uint8 public constant decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;

    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(string memory n, string memory s, uint256 supply) {
        name = n;
        symbol = s;
        totalSupply = supply;
        balanceOf[msg.sender] = supply;
        emit Transfer(address(0), msg.sender, supply);
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _move(msg.sender, to, value);
        return true;
    }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
        return true;
    }

    // OpenZeppelin Contracts 4.x にあった、今の許可から引く形の変更。
    function decreaseAllowance(address spender, uint256 sub) external returns (bool) {
        uint256 cur = allowance[msg.sender][spender];
        require(cur >= sub, "allowance below zero");
        allowance[msg.sender][spender] = cur - sub;
        emit Approval(msg.sender, spender, cur - sub);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        uint256 cur = allowance[from][msg.sender];
        require(cur >= value, "insufficient allowance");
        if (cur != type(uint256).max) {
            allowance[from][msg.sender] = cur - value;
        }
        _move(from, to, value);
        return true;
    }

    function _move(address from, address to, uint256 value) internal {
        require(balanceOf[from] >= value, "insufficient balance");
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
    }
}

// USDT（TetherToken）に似せた形。関数は何も返さず、0 でない許可を 0 以外へ直接は変えられない。
contract NoReturnToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);

    constructor(uint256 supply) { balanceOf[msg.sender] = supply; }

    function transfer(address to, uint256 value) external {
        require(balanceOf[msg.sender] >= value);
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
    }

    function approve(address spender, uint256 value) external {
        require(!((value != 0) && (allowance[msg.sender][spender] != 0)));
        allowance[msg.sender][spender] = value;
        emit Approval(msg.sender, spender, value);
    }

    function transferFrom(address from, address to, uint256 value) external {
        require(allowance[from][msg.sender] >= value);
        require(balanceOf[from] >= value);
        allowance[from][msg.sender] -= value;
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
    }
}

// 失敗しても revert せず false を返すトークン。
contract FalseToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed from, address indexed to, uint256 value);

    constructor(uint256 supply) { balanceOf[msg.sender] = supply; }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        return true;
    }

    function transfer(address to, uint256 value) external returns (bool) {
        if (balanceOf[msg.sender] < value) return false;
        balanceOf[msg.sender] -= value;
        balanceOf[to] += value;
        emit Transfer(msg.sender, to, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        if (allowance[from][msg.sender] < value || balanceOf[from] < value) return false;
        allowance[from][msg.sender] -= value;
        balanceOf[from] -= value;
        balanceOf[to] += value;
        emit Transfer(from, to, value);
        return true;
    }
}

// 移転のたびに 2% を手数料として焼くトークン。
contract FeeToken {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    event Transfer(address indexed from, address indexed to, uint256 value);

    constructor(uint256 supply) { balanceOf[msg.sender] = supply; }

    function approve(address spender, uint256 value) external returns (bool) {
        allowance[msg.sender][spender] = value;
        return true;
    }

    function transfer(address to, uint256 value) external returns (bool) {
        _move(msg.sender, to, value);
        return true;
    }

    function transferFrom(address from, address to, uint256 value) external returns (bool) {
        require(allowance[from][msg.sender] >= value);
        allowance[from][msg.sender] -= value;
        _move(from, to, value);
        return true;
    }

    function _move(address from, address to, uint256 value) internal {
        require(balanceOf[from] >= value);
        uint256 fee = value * 2 / 100;
        balanceOf[from] -= value;
        balanceOf[to] += value - fee;
        emit Transfer(from, to, value - fee);
        emit Transfer(from, address(0), fee);
    }
}

interface IERC20 {
    function transferFrom(address from, address to, uint256 value) external returns (bool);
    function balanceOf(address who) external view returns (uint256);
}

// 預け入れを 4 通りの書き方で受け取り、記帳した額を credited に残す。
contract Vault {
    mapping(address => mapping(address => uint256)) public credited; // token => user => 記帳した額

    // 1. 戻り値を require で見る。
    function depositRequire(address token, uint256 amount) external {
        require(IERC20(token).transferFrom(msg.sender, address(this), amount), "returned false");
        credited[token][msg.sender] += amount;
    }

    // 2. 戻り値を見ない。
    function depositIgnore(address token, uint256 amount) external {
        IERC20(token).transferFrom(msg.sender, address(this), amount);
        credited[token][msg.sender] += amount;
    }

    // 3. OpenZeppelin の SafeERC20 と同じ判定。空の戻り値か true なら成功とみなす。
    function depositSafe(address token, uint256 amount) external {
        _safeTransferFrom(token, msg.sender, amount);
        credited[token][msg.sender] += amount;
    }

    // 4. 3 に加えて、受け取る前後の残高の差を記帳する。
    function depositMeasured(address token, uint256 amount) external {
        uint256 before = IERC20(token).balanceOf(address(this));
        _safeTransferFrom(token, msg.sender, amount);
        credited[token][msg.sender] += IERC20(token).balanceOf(address(this)) - before;
    }

    function _safeTransferFrom(address token, address from, uint256 amount) internal {
        (bool ok, bytes memory ret) = token.call(
            abi.encodeWithSelector(IERC20.transferFrom.selector, from, address(this), amount)
        );
        require(ok && (ret.length == 0 || abi.decode(ret, (bool))), "transfer failed");
        require(ret.length > 0 || token.code.length > 0, "not a contract");
    }
}
