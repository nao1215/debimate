// SPDX-License-Identifier: MIT
// 説明用の実装。監査を受けておらず、実際の資産では使わない。
pragma solidity 0.8.28;

/// 入札額をそのまま送るオークション（比較用）。
contract OpenAuction {
    address public highestBidder;
    uint256 public highestBid;

    function bid(uint256 amount) external {
        require(amount > highestBid, "too low");
        highestBid = amount;
        highestBidder = msg.sender;
    }
}

/// コミットの段で入札額のハッシュを、リビールの段で入札額と salt を受け取るオークション。
contract CommitRevealAuction {
    uint256 public constant DEPOSIT = 1 ether;
    uint256 public immutable commitDeadline; // この高さまでのブロックでコミットを受け付ける
    uint256 public immutable revealDeadline; // この高さまでのブロックでリビールを受け付ける

    mapping(address => bytes32) public commitments;
    address public highestBidder;
    uint256 public highestBid;

    constructor(uint256 commitBlocks, uint256 revealBlocks) {
        commitDeadline = block.number + commitBlocks;
        revealDeadline = commitDeadline + revealBlocks;
    }

    function commit(bytes32 commitment) external payable {
        require(block.number <= commitDeadline, "commit closed");
        require(msg.value == DEPOSIT, "deposit");
        require(commitments[msg.sender] == bytes32(0), "already committed");
        commitments[msg.sender] = commitment;
    }

    function reveal(uint256 amount, bytes32 salt) external {
        require(block.number > commitDeadline, "too early");
        require(block.number <= revealDeadline, "reveal closed");
        // 送り主のアドレスもハッシュに含め、他人のコミットを写しても使えないようにする
        require(keccak256(abi.encode(msg.sender, amount, salt)) == commitments[msg.sender], "mismatch");
        delete commitments[msg.sender];
        if (amount > highestBid) {
            highestBid = amount;
            highestBidder = msg.sender;
        }
        payable(msg.sender).transfer(DEPOSIT); // リビールした人にだけ預け金を返す
    }
}
