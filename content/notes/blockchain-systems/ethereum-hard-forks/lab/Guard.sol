// SPDX-License-Identifier: MIT
// Educational code for a local experiment. Not audited.
pragma solidity 0.8.28;

contract Guard {
    bool transient locked;

    function run() external {
        require(!locked, "reentered");
        locked = true;
        locked = false;
    }
}
