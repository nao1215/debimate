// SPDX-License-Identifier: MIT
// Educational contract for a local experiment. Not audited.
pragma solidity 0.8.28;

import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {ERC20Permit} from "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

/// ERC-20 + ERC-2612 permit from OpenZeppelin Contracts v5.1.0.
/// EIP-712 domain: name "Study Token", version "1", chainId, address(this).
contract StudyPermitToken is ERC20, ERC20Permit {
    constructor(address holder) ERC20("Study Token", "STK") ERC20Permit("Study Token") {
        _mint(holder, 100);
    }

    function decimals() public pure override returns (uint8) {
        return 0;
    }
}
