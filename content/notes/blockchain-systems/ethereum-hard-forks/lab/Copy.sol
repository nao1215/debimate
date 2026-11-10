// SPDX-License-Identifier: MIT
// Educational code for a local experiment. Not audited.
pragma solidity 0.8.28;

contract Copy {
    function twice(bytes memory data) external pure returns (bytes memory) {
        return bytes.concat(data, data);
    }
}
