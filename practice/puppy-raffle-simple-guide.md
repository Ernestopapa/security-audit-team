# Puppy Raffle — simple practice guide
Started 2026-11-03. Code from public repo Cyfrin/2023-10-Puppy-Raffle, src/PuppyRaffle.sol, 216 lines.
Local copy: ~/workspace/security-audit-team/practice/puppy-raffle/src/PuppyRaffle.sol
Do NOT start the 7-day clock on CodeHawks until you have practised here first.

## What it is, in plain words
People pay to enter a raffle. After some time, one person wins a puppy NFT + 80% of all the money paid in. The owner keeps 20% as a fee.

## The 4 things it does
1. **Enter** — `enterRaffle`: pay the fee, your name goes on the list. No same name twice.
2. **Refund** — `refund`: get your fee back, your name is crossed off (set to 0).
3. **Pick a winner** — `selectWinner`: after time is up and at least 4 people entered, pick one name, send them 80%, mint them a puppy NFT, clear the list, start again.
4. **Take fees** — `withdrawFees`: owner takes the 20% — but only if no one is left playing.

## Money
- Entrance fee: set at the start, same for everyone.
- Winner gets 80%, owner gets 20%.

## Try these 5 questions first — do not read the answers below yet
1. Refund: it sends you money BEFORE it crosses your name off. What can a sneaky contract do?
2. Winner pick: it picks the winner using the time + who calls it + a number anyone can see. Can someone guess it first?
3. Enter twice: it checks for the same name AFTER it adds the new names to the list. What happens if one person enters twice?
4. Fees: it only lets the owner take fees if the money in the contract is EXACTLY equal to the fees. What if someone sends 1 tiny coin straight to the contract?
5. Many players: every time someone enters, it checks every name against every other name. What happens when 200 people have entered?

## Worked example — Question 1, in plain words
`refund` does this, in this order:
- send money to you
- THEN cross your name off

A normal person cannot ask twice fast enough. A sneaky contract can: when it gets the money, it automatically asks for a refund again, before its name is crossed off. It can do that over and over and drain the money.

Fix, in plain words: cross the name off FIRST, then send the money. Or add a lock so it cannot be called again while it is running.

## The other 4 — short hints, try them yourself
2. Winner: the "random" number is made from things everyone can see before the draw. A person can work it out, then call it at the right time to make themselves win.
3. Enter twice: because the check is after adding, one duplicate name blocks EVERYONE from entering after that. The raffle gets stuck.
4. Fees: if the balance is even 1 coin more than the fees, the exact check fails forever. Anyone can send 1 coin directly and lock the owner's fees.
5. Many players: the double-check gets slower and more expensive each time. After ~200 players, no one can afford to enter. Money gets stuck.

## How to submit on CodeHawks (when you are ready)
1. Make a free account on codehawks.cyfrin.io
2. First Flights > AI Judged > Puppy Raffle > Start Challenge — this starts your 7 days
3. Write each bug in plain words: what happens, who loses what, how to show it
4. Submit, get instant feedback, see what you missed

You submit under your own account. I help you read and test, you check and understand before you submit.
