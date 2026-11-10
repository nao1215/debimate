// SPDX-License-Identifier: CC0-1.0
// Educational example for the EVM note. Not audited.
pragma solidity 0.8.28;

// Calls itself `depth` times and returns gasleft() at the entry of the deepest frame.
contract Deep {
    function down(uint256 depth) external returns (uint256) {
        if (depth == 0) return gasleft();
        return this.down(depth - 1);
    }
}
