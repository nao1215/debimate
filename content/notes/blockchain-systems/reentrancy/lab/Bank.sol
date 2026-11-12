// SPDX-License-Identifier: MIT
// リエントランシー攻撃の説明用のコントラクト。監査を受けていない教材であり、実際の資産に使わない。
pragma solidity 0.8.28;

import {ReentrancyGuard} from "./oz/ReentrancyGuard.sol";
import {ReentrancyGuardTransient} from "./oz/ReentrancyGuardTransient.sol";

// (1) 脆弱な銀行: 送金してから残高を 0 にする
contract VulnerableBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: amount}(""); // ここで制御が相手に移る
        require(ok, "send failed");
        balances[msg.sender] = 0; // 相手が戻ってくるまで、残高は減っていない
    }

    function transferBalance(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "no balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

// (2) checks-effects-interactions: 残高を 0 にしてから送金する
contract CeiBank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external {
        uint256 amount = balances[msg.sender];   // checks
        require(amount > 0, "no balance");
        balances[msg.sender] = 0;                // effects
        (bool ok, ) = msg.sender.call{value: amount}(""); // interactions
        require(ok, "send failed");
    }

    function transferBalance(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "no balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

// (3) ロック: 並びは (1) のまま、OpenZeppelin の nonReentrant を付ける（storage の旗）
contract GuardedBank is ReentrancyGuard {
    mapping(address => uint256) public balances;

    function deposit() external payable nonReentrant {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external nonReentrant {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");
        balances[msg.sender] = 0;
    }

    // わざと nonReentrant を付けない関数（関数をまたぐリエントランシーの実験用）
    function transferBalance(address to, uint256 amount) external {
        require(balances[msg.sender] >= amount, "no balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

// (4) ロック: (3) と同じで、旗を transient storage（EIP-1153）に置く
contract TransientGuardedBank is ReentrancyGuardTransient {
    mapping(address => uint256) public balances;

    function deposit() external payable nonReentrant {
        balances[msg.sender] += msg.value;
    }

    function withdraw() external nonReentrant {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "no balance");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "send failed");
        balances[msg.sender] = 0;
    }

    function transferBalance(address to, uint256 amount) external nonReentrant {
        require(balances[msg.sender] >= amount, "no balance");
        balances[msg.sender] -= amount;
        balances[to] += amount;
    }
}

interface IBank {
    function deposit() external payable;
    function withdraw() external;
    function transferBalance(address to, uint256 amount) external;
}

// 攻撃側: ETH を受け取るたびに、銀行の withdraw を呼び直す
contract Attacker {
    IBank public immutable bank;
    address public immutable accomplice; // 関数をまたぐリエントランシーで残高を逃がす先
    bool public crossFunction;
    uint256 public calls;

    event Received(uint256 n, uint256 bankBalance);
    event Rejected(uint256 n, bytes reason);

    constructor(IBank bank_, address accomplice_) {
        bank = bank_;
        accomplice = accomplice_;
    }

    function attack(bool crossFunction_) external payable {
        crossFunction = crossFunction_;
        bank.deposit{value: msg.value}();
        bank.withdraw();
    }

    receive() external payable {
        calls++;
        emit Received(calls, address(bank).balance);
        if (crossFunction) {
            // 別の関数で、まだ減っていない残高を仲間へ移す
            if (calls == 1) {
                try bank.transferBalance(accomplice, msg.value) {} catch (bytes memory r) { emit Rejected(calls, r); }
            }
        } else if (address(bank).balance >= msg.value) {
            try bank.withdraw() {} catch (bytes memory r) { emit Rejected(calls, r); }
        }
    }
}

// 2300 gas の実験: storage を 1 回読んでログを出すだけの受け取り側
contract Receiver {
    uint256 public note = 42;
    event Got(uint256 note);

    receive() external payable {
        emit Got(note);
    }
}

contract Payer {
    function payWithTransfer(address payable to) external payable {
        to.transfer(msg.value); // 受け取り側に 2300 gas だけ渡す
    }

    function payWithCall(address payable to) external payable {
        (bool ok, ) = to.call{value: msg.value}(""); // 残りの gas の 63/64 まで渡す
        require(ok, "send failed");
    }
}
