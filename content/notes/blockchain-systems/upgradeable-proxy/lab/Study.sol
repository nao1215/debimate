// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

// Learning-only contracts for the upgradeable-proxy note. Not audited.
// Do not deploy them anywhere except a local development node.

abstract contract Delegate {
    function _delegate(address impl) internal {
        assembly {
            calldatacopy(0, 0, calldatasize())
            let ok := delegatecall(gas(), impl, 0, calldatasize(), 0, 0)
            returndatacopy(0, 0, returndatasize())
            switch ok
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
}

// 1. A proxy that keeps the implementation address in slot 0.
contract NaiveProxy is Delegate {
    address implementation; // slot 0

    constructor(address impl) {
        implementation = impl;
    }

    fallback() external payable {
        _delegate(implementation);
    }
}

// 2. A minimal ERC-1967 proxy. Only the admin can call upgradeTo(address);
//    every other call is forwarded to the implementation.
contract StudyProxy is Delegate {
    bytes32 internal constant IMPLEMENTATION_SLOT =
        bytes32(uint256(keccak256("eip1967.proxy.implementation")) - 1);
    bytes32 internal constant ADMIN_SLOT =
        bytes32(uint256(keccak256("eip1967.proxy.admin")) - 1);

    event Upgraded(address indexed implementation);
    event AdminChanged(address previousAdmin, address newAdmin);

    constructor(address impl) {
        _store(ADMIN_SLOT, msg.sender);
        emit AdminChanged(address(0), msg.sender);
        _upgrade(impl);
    }

    fallback() external payable {
        if (msg.sender == _load(ADMIN_SLOT) && msg.sig == bytes4(keccak256("upgradeTo(address)"))) {
            _upgrade(abi.decode(msg.data[4:], (address)));
            return;
        }
        _delegate(_load(IMPLEMENTATION_SLOT));
    }

    function _upgrade(address impl) private {
        require(impl.code.length > 0, "not a contract");
        _store(IMPLEMENTATION_SLOT, impl);
        emit Upgraded(impl);
    }

    function _store(bytes32 slot, address value) private {
        assembly { sstore(slot, value) }
    }

    function _load(bytes32 slot) private view returns (address value) {
        assembly { value := sload(slot) }
    }
}

// Implementations -------------------------------------------------------

contract CounterV1 {
    uint256 public count; // slot 0

    function increment() external {
        count += 1;
    }
}

contract VaultV1 {
    address public owner;  // slot 0
    uint256 public balance; // slot 1

    function setUp(address owner_, uint256 balance_) external {
        require(owner == address(0), "already set");
        owner = owner_;
        balance = balance_;
    }
}

// V2 that inserts a new variable at the top: every later variable shifts.
contract VaultV2Bad {
    uint256 public fee;     // slot 0 (was owner)
    address public owner;   // slot 1 (was balance)
    uint256 public balance; // slot 2 (empty)

    function setFee(uint256 fee_) external {
        fee = fee_;
    }
}

// V2 that appends the new variable at the end.
contract VaultV2Good {
    address public owner;   // slot 0
    uint256 public balance; // slot 1
    uint256 public fee;     // slot 2
}

// A constructor runs in the implementation's own storage, not in the proxy's.
contract CtorBox {
    uint256 public value;

    constructor() {
        value = 42;
    }
}

// ERC-7201 namespaced storage --------------------------------------------

contract NamespacedVault {
    /// @custom:storage-location erc7201:debimate.vault
    struct VaultStorage {
        address owner;
        uint256 balance;
    }

    // keccak256(abi.encode(uint256(keccak256("debimate.vault")) - 1)) & ~bytes32(uint256(0xff))
    bytes32 private constant VAULT_LOCATION =
        0xae0e5a2ac921da8c4f0db7a6df576631c5d91fc4de80e3189b369f9d39c30700;

    function _vault() private pure returns (VaultStorage storage $) {
        assembly { $.slot := VAULT_LOCATION }
    }

    function setUp(address owner_, uint256 balance_) external {
        VaultStorage storage $ = _vault();
        require($.owner == address(0), "already set");
        $.owner = owner_;
        $.balance = balance_;
    }

    function owner() external view returns (address) {
        return _vault().owner;
    }

    function balance() external view returns (uint256) {
        return _vault().balance;
    }
}

// Inheritance order: plain variables vs namespaces.
contract PlainA { uint256 public a; }
contract PlainB { uint256 public b; }
contract PlainAB is PlainA, PlainB {}
contract PlainBA is PlainB, PlainA {}
