// SPDX-License-Identifier: MIT
// Educational code for a local experiment. Not audited.
pragma solidity 0.8.28;

contract Sender {
    // transfer forwards only the 2300 gas stipend to the receiver.
    function pay(address payable to) external payable {
        to.transfer(msg.value);
    }
}
