// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

// Educational contracts for the ethereum-address note. Not audited.
// kill() has no access control on purpose; never deploy these with real funds.

contract Child {
    uint256 public immutable value;

    constructor(uint256 v) {
        value = v;
    }
}

contract Factory {
    // CREATE2: the address depends on this factory, salt and Child's initcode (with v).
    function deploy(bytes32 salt, uint256 v) external returns (address) {
        return address(new Child{salt: salt}(v));
    }

    // CREATE2 of a Deployer: same salt -> same Deployer address.
    function deployDeployer(bytes32 salt) external returns (address) {
        return address(new Deployer{salt: salt}());
    }
}

contract Deployer {
    // CREATE: the address depends on this Deployer and its nonce (starts at 1).
    function deploy(bytes memory initcode) external returns (address a) {
        assembly {
            a := create(0, add(initcode, 32), mload(initcode))
        }
        require(a != address(0), "create failed");
    }

    function kill() external {
        selfdestruct(payable(msg.sender));
    }
}

contract V1 {
    function version() external pure returns (uint256) {
        return 1;
    }

    function kill() external {
        selfdestruct(payable(msg.sender));
    }
}

contract V2 {
    function version() external pure returns (uint256) {
        return 2;
    }

    function kill() external {
        selfdestruct(payable(msg.sender));
    }
}
