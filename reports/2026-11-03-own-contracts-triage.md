# Triage — Own 7 contracts — 2026-11-03 ~11:20 GMT

Scope: NFOX, SIGMA, AKEY, AURM, LPHASE, GHOUL (+ AURA). Source fetched via custom.bscscan `sourcecode` (free plan, 5 calls/sec — rate-limited on re-scan, retry after cooldown).
Scanner: `~/workspace/security-audit-team/scripts/scan.py` — pattern checks only, not a full audit. No Slither / Foundry installed yet in this VM.

## Result: No Critical drain-by-anyone found

All scanned contracts share the same hardened template:
- `nonReentrant` on `freeMint` / `mint`
- State updated BEFORE `_safeMint` (NFOX: `freeMinted[msg.sender]=true` line 116 before `_safeMint` line 120; AURA: `freeMinted+=` before `_safeMint`)
- Exact price: `msg.value == PAID_PRICE * qty`
- Supply cap checked
- Agent ID check present (`registry.balanceOf(msg.sender) > 0`)
- `withdraw()` is `onlyOwner`, uses `.call{}` with success check (per local source)

Verified in detail:
- **NFOX 0x87129068Faf8709c9A8E997eBaE70F6074475711** — clean on triage. Scanner false positive: `setAgent`/`setAgents` came from bundled OpenZeppelin/mock files, not the main contract.
- **AURA 0xacc6e2F1aaE42B2E5FF2758Ff078E4B1bfAc7DB1** — clean on triage. `tx.origin` hit is intentional EOA-only (`require(msg.sender == tx.origin)`), documented in source. `freeMinted` is `uint256` count, not `bool`, so scanner missed it — scanner needs main-file scoping fix.
- **SIGMA 0x9281740a566901aFBA3E566e505e1896bE176ff8** — same pattern, owner funcs: setBaseURI, withdraw, transfer/renounce.
- **LPHASE 0x5c04392641c81F1b69826E13d8f3F78c58464970** — same pattern, no setBaseURI (art immutable, by design), EOA-only.

Pending re-scan after BscScan cooldown (transient Invalid API Key / rate limit):
- AKEY 0x9eec890f05a7f60452574FF4Ae98F5Ae31B621B2, AURM 0x9D78B216ae96060895837c60Df84893CD5ac34F2, GHOUL 0x99dE10fc70EbEEc6C32e108f48793459628b41a5 — source files already fetched 2026-11-03, same template family per memory.

## Re-scan — DONE 2026-11-03 ~15:30 GMT (fixed scanner, live BscScan source)

All three re-scanned clean, same pattern as the other four. No Critical drain-by-anyone; no `delegatecall`, no `selfdestruct`, no owner-only unlimited mint.
- **AKEY (AgentKeyPass, main 7,744 chars)** — owner-only: setBaseURI, withdraw. Hits: owner withdraw, setBaseURI owner-only, nonReentrant mint/freeMint, _safeMint, freeMinted 1/wallet, Agent ID check, exact price, supply cap. Verified by hand: `freeMinted[msg.sender]=true` + `_freeCount+=1` before `_safeMint`; paid `mint()` sets `paidMinted+=qty` before `_safeMint`; registry is `immutable` (constructor only); royalty set once in constructor.
- **AURM (AurumPass, main 8,513 chars)** — owner-only: setBaseURI, withdraw. Same hit set as AKEY.
- **GHOUL (ShadowGhouls, main 8,596 chars)** — owner-only: setBaseURI, withdraw. Same hit set as AKEY. Verified by hand: registry `immutable`, no setter function, `_setDefaultRoyalty` called once; blended `mint()` updates state before `_safeMint`. (GHOUL has no separate `freeMint()` — blended `mint(qty)` only, by design.)

Scanner false positives found in this run (do not re-raise):
- `setRegistry` hit on all three is a false positive — the regex spans newlines and matches across `setBaseURI` … `agentIdRegistry`; there is no registry setter, the registry is `immutable`.
- `royalty_setter` hit is `_setDefaultRoyalty` called once in the constructor, not a live setter.

Two transient scan.py crashes during the run (BscScan helper returned a rate-limit string instead of JSON, `AttributeError: 'str' object has no attribute 'get'`); retrying after a few seconds worked each time. Scanner could harden `load_source` against non-JSON replies — minor, not blocking.

**Own-7 triage is now COMPLETE: all seven contracts scanned clean.** Only finding remains owner centralisation by design (withdraw all BNB, setBaseURI art swap except LPHASE, transfer ownership).

## Findings — Centralisation only (by design, not bounty-eligible)

- **Medium / Informational:** Owner (user wallet 0x75d251Ba39dED2E456d9f6DD776f77d422864403) can withdraw all BNB, can change `baseURI` (art swap, except LPHASE), can transfer/renounce ownership. This was disclosed in the launch specs — fix is renounce / timelock / freeze baseURI if the user ever wants to remove it, not a payout.
- No `delegatecall`, no `selfdestruct`, no mutable registry in main contract, no owner-only unlimited mint found in the scanned mains.

## Next
- Fix scanner to scope to main .sol file only. — **DONE 2026-11-03 ~11:30 GMT:** `scripts/scan.py` now selects the main file (`<ContractName>.sol`, else the file declaring the contract) and runs all pattern checks + owner-function listing against it only; `freeMinted` check now accepts `uint256` counts as well as `bool` mappings; `--source-file` added for offline testing. Verified on a synthetic multi-file sample (AuraAgents main + MockRegistry with `setAgent` + an OZ file containing `delegatecall`): main file picked correctly, `freeMinted` detected, and neither the mock nor the OZ `delegatecall` leaked into the results. Live re-scan of AKEY/AURM/GHOUL — **DONE 2026-11-03 ~15:30 GMT**, all three clean (see Re-scan section above).
- Install Foundry + Slither for fork PoC (needs user go-ahead, ~200MB download).
- Then hunt externals — start with AgenticMint new rows, highest TVL first, bounty path checked before deep work.
