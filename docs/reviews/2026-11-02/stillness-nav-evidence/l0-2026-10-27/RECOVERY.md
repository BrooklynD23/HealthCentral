# L0 2026-10-27 evidence copy: recovery note and sha256 check

Task 1 step 1 of STILLNESS-NAV-LATE (docs/plans/2026-10-23-frontend-revamp-plan.md, "Evidence to keep").

## How these files were recovered

L0 wrote the scripts and logs to its session scratchpad (`/tmp/claude-1000/.../b8becc8c-.../scratchpad/`). That
scratchpad was wiped before this row started. L1 recovered 16 of the 18 files from the old session transcript
(the tool-call inputs that wrote the scripts and the tool results that printed the logs), then handed the
recovered directory to the Task 1 implementer. The implementer ran `sha256sum` on the committed copies itself
and compared each against the plan's table. The raw `sha256sum` output is in the second block below.

`probecost/gates.instrumented.ts` is the instrumented copy that the plan names `probecost/e2e/support/gates.ts`.
It was rebuilt from the branch's `gates.ts` at commit 397ea8f3 plus L0's PROBECOST patch; its hash matches.

## Two files are lost

| Plan name | Plan sha256 | Committed instead |
|---|---|---|
| `baretimer/t4-preview.log` | `91e3cf6fa569` | `baretimer/t4-preview.FILTERED-not-original.log` (`24511fcf9bf3`) |
| `probecost/probe-runs.log` | `c139049e251b` | `probecost/probe-runs.FILTERED-not-original.log` (`9302fce73d4c`) |

Only filtered views of these two logs survive in the transcript (the `grep`/`sed` output L0 saw, not the file).
The originals are lost, and their hashes cannot be checked. The `*.FILTERED-not-original.log` files are NOT the
originals and must not be cited as if they were. The plan's table rows that cite them ("9 of 15", "8 of 15",
"8 of 15", "2 of 36") rest on those filtered views.

## sha256 against the plan table (first 12 hex digits)

| File | Plan table | `sha256sum` of the committed copy | Result |
|---|---|---|---|
| `baretimer/baretimer.spec.ts` | `95c225c36f8a` | `95c225c36f8a` | match |
| `baretimer/playwright.config.ts` | `6ed971971960` | `6ed971971960` | match |
| `baretimer/run_batch.sh` | `4d3506bcf645` | `4d3506bcf645` | match |
| `baretimer/wait_quiet.sh` | `3008f372b0fd` | `3008f372b0fd` | match |
| `baretimer/t4_preview.sh` | `91916bb4ecc1` | `91916bb4ecc1` | match |
| `baretimer/batch0.log` | `8bc42a492c2c` | `8bc42a492c2c` | match |
| `baretimer/batch1.log` | `bacc5213b3b8` | `bacc5213b3b8` | match |
| `baretimer/batch2.log` | `04a872243e9b` | `04a872243e9b` | match |
| `baretimer/batch3.log` | `9f3e239a9c6a` | `9f3e239a9c6a` | match |
| `baretimer/batch4.log` | `b89f4d07aa63` | `b89f4d07aa63` | match |
| `baretimer/batch5.log` | `ee72cd494c3d` | `ee72cd494c3d` | match |
| `baretimer/probe-control.log` | `94e867b7b087` | `94e867b7b087` | match |
| `baretimer/t4-preview.log` | `91e3cf6fa569` | not recovered (committed instead as `baretimer/t4-preview.FILTERED-not-original.log`, `24511fcf9bf3`) | LOST, cannot be checked |
| `probecost/gates.instrumented.ts` | `b49473df8217` | `b49473df8217` | match |
| `probecost/main-probe.spec.ts` | `59af43d9db7c` | `59af43d9db7c` | match |
| `probecost/playwright.config.ts` | `e253e44fa2bb` | `e253e44fa2bb` | match |
| `probecost/run_probe.sh` | `0736ce5bd83d` | `0736ce5bd83d` | match |
| `probecost/probe-runs.log` | `c139049e251b` | not recovered (committed instead as `probecost/probe-runs.FILTERED-not-original.log`, `9302fce73d4c`) | LOST, cannot be checked |

## Raw `sha256sum` output (full digests, run in this directory)

```
95c225c36f8adcc6e2fd730afb0d9c1b78c8ced1b27556f78c0fd4698851f2e1  ./baretimer/baretimer.spec.ts
8bc42a492c2c3f70cb236efd70563d531b2191b4c1f48c4e871a8534bd7cce05  ./baretimer/batch0.log
bacc5213b3b8608906cc8a3a95ac2c63c624a4b7d387d855a58bac74fc2e54ed  ./baretimer/batch1.log
04a872243e9b6edbcf8dd290650fd0f7e1b92963349f344e2b2821798096208b  ./baretimer/batch2.log
9f3e239a9c6a10192dc546510a279291f01955f59b23de426ee00997e493b6f2  ./baretimer/batch3.log
b89f4d07aa63e4d551ed51575cf864cd109d4923814e933696fabf3be966ee86  ./baretimer/batch4.log
ee72cd494c3d569f574755ea42a801c2ba8f1a1440d45cd77c1e206035b38748  ./baretimer/batch5.log
6ed971971960ea6036be96be60a77f4be00d8c7166481a7eae1bed5a3bcf9157  ./baretimer/playwright.config.ts
94e867b7b087621815e86f7432861230ffad77480a9554f01d03062d26daac68  ./baretimer/probe-control.log
4d3506bcf6450cbe026c6ef36776cf9c223e95500d92497abc898d3caf873004  ./baretimer/run_batch.sh
24511fcf9bf345e61f84debde9b97f1fe25d07b42e5be7f14533af6bf0c24fe1  ./baretimer/t4-preview.FILTERED-not-original.log
91916bb4ecc14c540376d1eac13fe02d86ed51b55e53f0059495049db29f7869  ./baretimer/t4_preview.sh
3008f372b0fd6232f69ae9b6d043905801e27dd83ea0986c0d8b91f6c838bef2  ./baretimer/wait_quiet.sh
b49473df8217c995f79068706cda916b13a5d3fe2c448e9b7e96dcb83a3a97e7  ./probecost/gates.instrumented.ts
59af43d9db7c54b247924285da00239e32c56fe05641f186906e9c792e0457c0  ./probecost/main-probe.spec.ts
e253e44fa2bbeb2bc8d9100bbf35fc646ae8fe1fb85741b66e8cb45e277cd12c  ./probecost/playwright.config.ts
9302fce73d4cfdd6cb9d6366a1de0078f5953ac86671f1e90bac95b5f7dbd739  ./probecost/probe-runs.FILTERED-not-original.log
0736ce5bd83d92883478b4b225bd9afe9496097d701efe182f1edc78dc5ad88a  ./probecost/run_probe.sh
```
