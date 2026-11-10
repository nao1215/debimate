// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

interface IERC721 {
    function transferFrom(address from, address to, uint256 tokenId) external;
}

// The Counter of the Smart Contract note with only increment(): it knows nothing about NFTs.
contract Counter {
    uint256 public count;
    event Changed(uint256 value);

    function increment() external {
        count += 1;
        emit Changed(count);
    }
}

// Educational receiver; no production security audit.
contract StudyReceiver {
    address public immutable keeper;

    constructor() {
        keeper = msg.sender;
    }

    function onERC721Received(address, address, uint256, bytes calldata) external pure returns (bytes4) {
        return this.onERC721Received.selector;
    }

    function withdraw(address nft, address to, uint256 tokenId) external {
        require(msg.sender == keeper, "keeper only");
        IERC721(nft).transferFrom(address(this), to, tokenId);
    }
}
