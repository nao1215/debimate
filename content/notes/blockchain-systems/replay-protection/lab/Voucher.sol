// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

/// 発行者が署名した引換券（Claim）を出すと、コントラクトが ETH を払う。学習用で、監査は受けていない。
/// mode で EIP-712 の domain の作り方だけを変える。
///   0: name と version だけ（chainId と verifyingContract を入れない）
///   1: chainId と verifyingContract を入れ、デプロイ時に計算して固定する
///   2: chainId と verifyingContract を入れ、検証のたびに計算する
contract Voucher {
    bytes32 constant CLAIM_TYPEHASH =
        keccak256("Claim(address to,uint256 amount,uint256 nonce,uint256 deadline)");
    bytes32 constant FULL_DOMAIN_TYPEHASH =
        keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)");
    bytes32 constant SHORT_DOMAIN_TYPEHASH = keccak256("EIP712Domain(string name,string version)");

    address public immutable issuer;
    uint8 public immutable mode;
    bytes32 immutable cachedSeparator;
    mapping(uint256 => bool) public used; // アプリ側の nonce: 使った番号を覚える

    constructor(address issuer_, uint8 mode_) payable {
        issuer = issuer_;
        mode = mode_;
        cachedSeparator = _separator();
    }

    function _separator() internal view returns (bytes32) {
        if (mode == 0) {
            return keccak256(abi.encode(SHORT_DOMAIN_TYPEHASH, keccak256("Voucher"), keccak256("1")));
        }
        return keccak256(abi.encode(
            FULL_DOMAIN_TYPEHASH, keccak256("Voucher"), keccak256("1"), block.chainid, address(this)));
    }

    function domainSeparator() public view returns (bytes32) {
        return mode == 2 ? _separator() : cachedSeparator;
    }

    function claim(address to, uint256 amount, uint256 nonce, uint256 deadline, uint8 v, bytes32 r, bytes32 s)
        external
    {
        require(block.timestamp <= deadline, "expired");
        require(!used[nonce], "nonce used");
        bytes32 structHash = keccak256(abi.encode(CLAIM_TYPEHASH, to, amount, nonce, deadline));
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domainSeparator(), structHash));
        require(ecrecover(digest, v, r, s) == issuer, "bad signature");
        used[nonce] = true;
        payable(to).transfer(amount);
    }
}
