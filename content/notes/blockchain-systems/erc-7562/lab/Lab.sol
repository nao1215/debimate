// SPDX-License-Identifier: MIT
// Learning contracts for the ERC-7562 note. Not audited. Do not deploy.
// Signature checks are left out on purpose: anyone could use these accounts.
pragma solidity 0.8.28;

import {PackedUserOperation} from "contracts/interfaces/PackedUserOperation.sol";

abstract contract LabAccount {
    address public immutable entryPoint;

    constructor(address ep) {
        entryPoint = ep;
    }

    function validateUserOp(PackedUserOperation calldata, bytes32, uint256 missingAccountFunds)
        external
        returns (uint256 validationData)
    {
        require(msg.sender == entryPoint, "not EntryPoint");
        validationData = _check();
        if (missingAccountFunds > 0) {
            (bool ok,) = payable(msg.sender).call{value: missingAccountFunds}("");
            ok;
        }
    }

    function _check() internal view virtual returns (uint256);

    function execute(address to, uint256 value, bytes calldata data) external {
        require(msg.sender == entryPoint, "not EntryPoint");
        (bool ok,) = to.call{value: value}(data);
        require(ok, "call failed");
    }

    receive() external payable {}
}

// Reads TIMESTAMP inside validation (OP-011).
contract TimeAccount is LabAccount {
    uint256 public immutable deadline;

    constructor(address ep, uint256 d) LabAccount(ep) {
        deadline = d;
    }

    function _check() internal view override returns (uint256) {
        require(block.timestamp < deadline, "too late");
        return 0;
    }
}

// Same intent, but returns validUntil and lets the EntryPoint compare it.
contract DeadlineAccount is LabAccount {
    uint48 public immutable deadline;

    constructor(address ep, uint48 d) LabAccount(ep) {
        deadline = d;
    }

    function _check() internal view override returns (uint256) {
        return uint256(deadline - 1) << 160; // validUntil, inclusive
    }
}

// A switch in another contract that anyone's account may depend on.
contract Gate {
    address public immutable owner = msg.sender;
    bool public isOpen = true;

    function close() external {
        require(msg.sender == owner, "not owner");
        isOpen = false;
    }
}

// Reads a slot of Gate that is not associated with the account (STO-021 fails).
contract GateAccount is LabAccount {
    Gate public immutable gate;

    constructor(address ep, Gate g) LabAccount(ep) {
        gate = g;
    }

    function _check() internal view override returns (uint256) {
        require(gate.isOpen(), "gate closed");
        return 0;
    }
}

contract LabToken {
    mapping(address => uint256) public balanceOf; // slot 0

    function mint(address to, uint256 v) external {
        balanceOf[to] += v;
    }
}

// Reads balanceOf[this] in a token: keccak(this || 0), associated storage (STO-021 allows).
contract TokenAccount is LabAccount {
    LabToken public immutable token;

    constructor(address ep, LabToken t) LabAccount(ep) {
        token = t;
    }

    function _check() internal view override returns (uint256) {
        require(token.balanceOf(address(this)) > 0, "no token");
        return 0;
    }
}

// Reads its own ETH balance with SELFBALANCE (OP-080: staked entities only).
contract BalanceAccount is LabAccount {
    constructor(address ep) LabAccount(ep) {}

    function _check() internal view override returns (uint256) {
        require(address(this).balance > 0, "empty");
        return 0;
    }
}
