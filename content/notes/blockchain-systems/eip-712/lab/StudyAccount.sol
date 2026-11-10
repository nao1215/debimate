// SPDX-License-Identifier: MIT
// Educational contract for a local experiment. Not audited.
pragma solidity 0.8.28;

import {IERC1271} from "@openzeppelin/contracts/interfaces/IERC1271.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";

/// A minimal account that "signs" through ERC-1271: a signature is valid
/// when it was made by the owner EOA. It does not rehash with its own
/// address, so the same signature is also valid for another StudyAccount
/// of the same owner (see ERC-7739 for that problem).
contract StudyAccount is IERC1271 {
    address public immutable owner;

    constructor(address owner_) {
        owner = owner_;
    }

    function isValidSignature(bytes32 hash, bytes calldata signature) external view returns (bytes4) {
        (address recovered, ECDSA.RecoverError err, ) = ECDSA.tryRecover(hash, signature);
        if (err == ECDSA.RecoverError.NoError && recovered == owner) {
            return IERC1271.isValidSignature.selector; // 0x1626ba7e
        }
        return 0xffffffff;
    }
}
