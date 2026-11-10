// SPDX-License-Identifier: MIT
// Educational contract for a local experiment. Not audited.
pragma solidity 0.8.28;

import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {SignatureChecker} from "@openzeppelin/contracts/utils/cryptography/SignatureChecker.sol";

/// Two ways an application might check "did `signer` sign `hash`?".
contract SigCheck {
    /// Recover the address from the signature only (ecrecover).
    function recover(bytes32 hash, bytes calldata signature) external pure returns (address) {
        (address recovered, , ) = ECDSA.tryRecover(hash, signature);
        return recovered;
    }

    /// ecrecover only: works for EOAs, never for contract accounts.
    function checkEcrecover(address signer, bytes32 hash, bytes calldata signature) external pure returns (bool) {
        (address recovered, ECDSA.RecoverError err, ) = ECDSA.tryRecover(hash, signature);
        return err == ECDSA.RecoverError.NoError && recovered == signer;
    }

    /// ecrecover for addresses without code, ERC-1271 for contracts.
    function checkWith1271(address signer, bytes32 hash, bytes calldata signature) external view returns (bool) {
        return SignatureChecker.isValidSignatureNow(signer, hash, signature);
    }
}
