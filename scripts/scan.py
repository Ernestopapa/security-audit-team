#!/usr/bin/env python3
"""Quick triage scanner for BSC Agent ID mint contracts.
Usage: python3 scan.py <address> [--source-file /tmp/x.json]
- Fetches verified source via the custom.bscscan helper if no file given.
- Runs pattern checks from PLAYBOOK.md §2, prints JSON triage.
- Read-only. No transactions, no mainnet calls that move funds.
"""
import json, re, subprocess, sys, pathlib

CHECKS = [
    ("owner_withdraw", r"function withdraw\(\)[^{]*\{[^}]*owner\(\)|payable\(owner\(\)\)\.call", "Owner can withdraw all BNB"),
    ("onlyowner_missing_withdraw", r"function withdraw\(\)\s*external(?!\s+onlyOwner)", "withdraw() without onlyOwner — check manually"),
    ("setBaseURI_owner", r"function setBaseURI.*onlyOwner", "setBaseURI is owner-only (can swap art — flag as centralisation)"),
    ("setBaseURI_no_owner", r"function setBaseURI\(.*\)\s*external\s*\{", "setBaseURI WITHOUT onlyOwner — anyone can swap metadata"),
    ("reentrancy_guard_mint", r"function (freeMint|mint)\([^)]*\)[^{]*nonReentrant", "mint/freeMint has nonReentrant"),
    ("safeMint_used", r"_safeMint\(", "_safeMint used (reentrancy surface if state after mint)"),
    ("freeMinted_mapping", r"mapping\(address => (bool|uint256)\)\s+public\s+freeMinted", "freeMinted 1/wallet mapping/count present"),
    ("agent_check_free", r"agentIdRegistry\.balanceOf\(msg\.sender\) > 0", "Agent ID check present"),
    ("price_exact", r"msg\.value == .*PAID_PRICE|msg\.value == .*price", "Exact price check present"),
    ("price_gte", r"msg\.value >= .*PAID_PRICE|require\(msg\.value >=", "Price uses >= — overpay may lock, check refund"),
    ("max_supply_check", r"totalSupply\(\) \+ qty <= MAX_SUPPLY|totalSupply\(\) < MAX_SUPPLY", "Supply cap checked in mint"),
    ("delegatecall", r"delegatecall", "DELEGATECALL present — high risk"),
    ("selfdestruct", r"selfdestruct|suicide\(", "SELFDESTRUCT present — high risk"),
    ("setRegistry", r"function set.*[Rr]egistry", "Registry mutable — owner can swap gate"),
    ("mint_owner_only", r"function mint\([^)]*\)[^{]*onlyOwner", "Owner-only mint — can mint unlimited if no cap"),
    ("transfer_owner", r"transferOwnership|renounceOwnership", "Ownership transfer present"),
    ("royalty_setter", r"function set.*[Rr]oyalty|_setDefaultRoyalty", "Royalty setter present"),
    ("tx_origin", r"tx\.origin", "tx.origin used — phishing / spoof risk"),
    ("block_timestamp_random", r"block\.timestamp.*%|keccak256\(abi\.encodePacked\(block", "Block timestamp/hash randomness — manipulable"),
]

def split_sources(src, contract_name):
    """Split BscScan multi-file source into (joined, main_file_name, main_source).

    Main file = the file named <ContractName>.sol, else the file declaring
    `contract <ContractName>`, else the first file. Bundled OpenZeppelin /
    mock files are returned only as part of the joined text, never as the
    scan target — that was the 2026-11-03 false positive (setAgent/setAgents
    from a mock file flagged against NFOX).
    """
    if not src.startswith("{{"):
        return src, "<single-file>", src
    try:
        inner = json.loads(src[1:-1])
    except Exception:
        return src, "<unparsed>", src
    files = {}
    for name, f in inner.get("sources", {}).items():
        files[name] = f.get("content", "")
    joined = "\n".join(f"// ==== {n} ====\n{c}" for n, c in files.items())
    main_name, main_src = None, None
    if contract_name:
        want = contract_name + ".sol"
        for n, c in files.items():
            if n.rsplit("/", 1)[-1] == want:
                main_name, main_src = n, c
                break
        if main_src is None:
            decl = re.compile(r"contract\s+" + re.escape(contract_name) + r"\b")
            for n, c in files.items():
                if decl.search(c):
                    main_name, main_src = n, c
                    break
    if main_src is None and files:
        main_name, main_src = next(iter(files.items()))
    return joined, main_name or "<none>", main_src or ""

def load_source(address):
    out = subprocess.run(["python3", str(pathlib.Path.home()/"workspace/custom-connectors/custom.bscscan/bin/bscscan.py"), "sourcecode", address],
                         capture_output=True, text=True, timeout=60)
    try:
        data = json.loads(out.stdout)
    except Exception:
        return None, None, f"bscscan parse failed: {out.stdout[:500]} {out.stderr[:500]}"
    return parse_bscscan_data(data)

def parse_bscscan_data(data):
    src = data.get("SourceCode", "")
    if not src or src == "Contract source code not verified":
        return None, None, "unverified"
    joined, main_name, main_src = split_sources(src, data.get("ContractName", ""))
    return joined, (main_name, main_src), data.get("ContractName", "")

def load_source_file(path):
    """Offline/test path: read a JSON file shaped like BscScan's reply
    ({"SourceCode": ..., "ContractName": ...}) or a raw .sol file."""
    text = pathlib.Path(path).read_text()
    if path.endswith(".json"):
        return parse_bscscan_data(json.loads(text))
    name = pathlib.Path(path).stem
    return text, (path, text), name

def main():
    if len(sys.argv) < 2:
        print("usage: scan.py <address> [--source-file /tmp/x.json]"); sys.exit(2)
    address = sys.argv[1]
    source_file = None
    if "--source-file" in sys.argv:
        source_file = sys.argv[sys.argv.index("--source-file") + 1]
        src, main, name = load_source_file(source_file)
    else:
        src, main, name = load_source(address)
    if src is None:
        print(json.dumps({"address": address, "status": "unverified_or_error", "detail": name}, indent=2))
        return
    main_name, main_src = main
    # Checks run against the MAIN contract file only, not bundled libs/mocks.
    hits = []
    for key, pat, desc in CHECKS:
        if re.search(pat, main_src, re.S):
            hits.append({"check": key, "note": desc})
    # Owner powers summary — main file only.
    owner_funcs = re.findall(r"function (\w+)\([^)]*\)[^{]*onlyOwner", main_src)
    print(json.dumps({
        "address": address,
        "contract": name,
        "main_file": main_name,
        "source_chars": len(src),
        "main_chars": len(main_src),
        "owner_only_functions": sorted(set(owner_funcs)),
        "hits": hits,
        "next": "Manual review needed for: reentrancy order (state before _safeMint?), free/paid counters, withdraw call success check, setBaseURI freeze."
    }, indent=2))

if __name__ == "__main__":
    main()
