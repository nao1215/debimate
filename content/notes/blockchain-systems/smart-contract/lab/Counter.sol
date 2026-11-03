// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

contract Counter {
    uint256 public count;
    event Changed(uint256 value);

    function increment() external {
        count += 1;
        emit Changed(count);
    }

    function incrementAndFail() external {
        count += 1;
        emit Changed(count);
        revert("demonstration");
    }
}
