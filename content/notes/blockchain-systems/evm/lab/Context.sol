// SPDX-License-Identifier: CC0-1.0
// Educational example for the EVM note. Not audited.
pragma solidity 0.8.28;

// Target and Caller share the same storage layout (slot 0 = count).
contract Target {
    uint256 public count;

    // Writes storage, then reports what the running code sees.
    function record() external payable returns (address sender, address self, uint256 value) {
        count += 1;
        return (msg.sender, address(this), msg.value);
    }

    // Same report without writing storage.
    function peek() external view returns (address sender, address self, uint256 value) {
        return (msg.sender, address(this), 0);
    }
}

contract Caller {
    uint256 public count;
    event Seen(string mode, bool ok, address sender, address self, uint256 value);

    // Called with msg.value = 7 wei.
    function run(address target) external payable {
        bytes memory rec = abi.encodeCall(Target.record, ());
        (bool ok, bytes memory ret) = target.call{value: 3}(rec);
        _report("CALL record", ok, ret);
        (ok, ret) = target.delegatecall(rec);
        _report("DELEGATECALL record", ok, ret);
        (ok, ret) = target.staticcall(rec);
        _report("STATICCALL record", ok, ret);
        (ok, ret) = target.staticcall(abi.encodeCall(Target.peek, ()));
        _report("STATICCALL peek", ok, ret);
    }

    function _report(string memory mode, bool ok, bytes memory ret) private {
        if (!ok) {
            emit Seen(mode, false, address(0), address(0), 0);
            return;
        }
        (address sender, address self, uint256 value) = abi.decode(ret, (address, address, uint256));
        emit Seen(mode, true, sender, self, value);
    }
}
