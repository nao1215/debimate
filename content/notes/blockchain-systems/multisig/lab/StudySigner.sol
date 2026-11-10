// SPDX-License-Identifier: MIT
pragma solidity >=0.7.0 <0.9.0;

// Learning-only ERC-1271 signer. Not audited. Do not deploy with real assets.
// The admin approves a hash in advance; the Safe then asks this contract
// whether the hash is approved instead of recovering an ECDSA key.
contract StudySigner {
    bytes4 internal constant MAGIC = 0x1626ba7e; // isValidSignature(bytes32,bytes)
    address public immutable admin;
    mapping(bytes32 => bool) public approved;

    constructor(address admin_) {
        admin = admin_;
    }

    function approve(bytes32 hash) external {
        require(msg.sender == admin, "not admin");
        approved[hash] = true;
    }

    function isValidSignature(bytes32 hash, bytes calldata) external view returns (bytes4) {
        return approved[hash] ? MAGIC : bytes4(0xffffffff);
    }
}
