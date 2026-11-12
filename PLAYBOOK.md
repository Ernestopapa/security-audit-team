# Audit Playbook — BSC Agent ID mints

## 1. Intake — where targets come from

- AgenticMint.ai radar (free + paid rows, Sourcify-verified first)
- X KOL watch: @joganicpe, @income360pro, @mrchrismast_, @trngne0510, @ibtc2023 (paused 2026-11-02 — re-enable only for intake, not auto-mint)
- BscScan verified contracts, recent deployments
- Your own 7 contracts first — proof the pipeline works before touching strangers.

Do NOT mint / buy to "test" a stranger's contract on mainnet. Read-only + fork only.

## 2. Triage — 15 minutes per contract

Fetch source via:
```
python3 ~/workspace/custom-connectors/custom.bscscan/bin/bscscan.py sourcecode <address>
```
If `SourceCode` empty → unverified → stop, log as unverified.

Then run `scripts/scan.py <address>` — it flags:

1. **Owner can drain / rug:** `withdraw()` to owner, `transferOwnership`, `renounce` missing, owner = EOA vs multisig, can owner change price / supply / baseURI / registry after launch?
2. **Owner can mint unlimited / bypass supply:** `onlyOwner mint`, no `MAX_SUPPLY` check, `_nextId` not capped.
3. **Free-mint bypass:** `freeMinted` mapping missing, or keyed by token not wallet, or resettable by owner; `freeMint` without Agent ID check; `msg.sender` vs `tx.origin` confusion.
4. **Paid-mint price bypass:** `msg.value` not checked, `>=` instead of `==` (overpay locked, or underpay with qty trick), qty 0, qty overflow, `paidMinted` not incremented before mint (reentrancy window).
5. **Reentrancy:** external call (`call`, `transfer`, `_safeMint` to receiver) before state update; missing `nonReentrant` on `mint` / `withdraw` / `freeMint`.
6. **Registry spoof:** registry address mutable (`setRegistry`), or zero-check missing, or `balanceOf` on wrong interface (returns 0/1 always).
7. **setBaseURI rug:** owner can swap metadata to rickroll / different art after mint; no timelock, no freeze.
8. **Royalty / fee trap:** `setDefaultRoyalty` callable by owner to 100%, or fee-on-transfer.
9. **Random / reveal manipulation:** `block.timestamp` / `blockhash` for traits, owner can pick token IDs.
10. **Access control missing:** `withdraw`, `setBaseURI`, `setPrice`, `pause` without `onlyOwner`.
11. **Denial / griefing:** `freeMint` loop that can run out of gas, `mint` loop unbounded qty, `withdraw` that reverts if owner is a contract.
12. **ERC-721 compliance:** `_safeMint` vs `_mint` to contracts, `tokenURI` reverts after baseURI unset, `supportsInterface` broken (marketplace won't index).
13. **Proxy / upgrade trap:** proxy admin can swap logic, implementation not verified.
14. **Hidden mint / backdoor:** `mint` with secret function name, `selfdestruct`, `delegatecall` to arbitrary address.
15. **Economic:** paid price in BNB hard-coded while BNB moves, max paid revenue tiny vs gas — is there even anything to steal? If contract holds <$5 and no bounty, deprioritise.

Score: Critical = funds / NFTs can be taken by anyone, or owner can rug all holders. High = owner can mint unlimited / change core rules, or anyone can mint free repeatedly. Medium = metadata / royalty / griefing. Low / Informational = gas, naming, docs.

## 3. Clone patterns to hunt first (highest hit-rate)

Most of these launches are copy-paste of 3 templates: AHLAND / NFOX-style, QUIRKZ-style, sidecoo GOLD-style. The same bug in one clone is usually in 20 clones.

- Missing `freeMinted[msg.sender]=true` BEFORE `_safeMint` (reentrancy via ERC721Receiver can re-enter freeMint)
- `mint()` checks `totalSupply()+qty <= MAX` but `freeMint()` doesn't increment the same counter, so free + paid can exceed MAX
- `withdraw()` uses `.transfer()` / `.send()` (2300 gas, fails) vs `.call{}` — or no `require(ok)`
- `setBaseURI` with no event, no freeze — silent art swap
- Paid phase gate uses `freeMintedCount` that owner can manipulate, or no gate at all — paid mintable during free phase
- `MAX_PAID_PER_TX` checked, but no per-wallet cap — one wallet drains paid supply in many txs (not a bug per se, but a design finding to report as Medium if the site promises 1/wallet)

## 4. Proof — fork only

- Never run PoC against mainnet state with real value.
- Use Anvil fork of BSC, impersonate attacker, show: before balance, call, after balance / token count. Save tx trace + script in `evidence/<project>/`.
- If no Foundry in VM, install it first (see scripts/install_tools.sh — not run without your go-ahead, it downloads ~200MB).
- A finding without a fork PoC is a hypothesis, not a submission.

## 5. Disclosure

Use `reports/TEMPLATE.md`. Send via:
1. Immunefi / Cantina / HackenProof program page if listed
2. Else `security@<domain>` / team X DM / Telegram, with title + impact + "full PoC available on acknowledgement" — do NOT send the full exploit in the first message to an anon team
3. Else SEAL 911 only if Critical + actively exploited right now

Track: date sent, ack date, fix tx, payout, tx hash. No payout = no public post.

## 6. What we do NOT do

- No mainnet exploitation, no "test drain and return it" — returning it does not make it white-hat.
- No extortion ("pay or I disclose").
- No auditing a contract to then launch a copy that exploits it.
- No submitting the same finding twice to the same program.
