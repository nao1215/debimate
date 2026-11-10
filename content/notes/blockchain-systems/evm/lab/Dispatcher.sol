// SPDX-License-Identifier: CC0-1.0
// Educational example for the EVM note. Not audited.
pragma solidity 0.8.28;

contract Dispatcher {
    uint256 public value;
    event Changed(address indexed sender, uint256 value);

    function set(uint256 x) external {
        value = x;
        emit Changed(msg.sender, x);
    }
}
