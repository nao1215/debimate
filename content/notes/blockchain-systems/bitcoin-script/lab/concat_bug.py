#!/usr/bin/env python3
"""A toy model of how Bitcoin 0.3.x ran the two scripts (standard library only).

Not a Bitcoin implementation: only OP_1, OP_RETURN, a data push and a stub
OP_CHECKSIG exist. The point is the order of evaluation.

- up to 0.3.4: EvalScript(scriptSig + OP_CODESEPARATOR + scriptPubKey), and
  OP_RETURN jumped to the end of the (joined) script ("pc = pend").
- 0.3.5 fixed it (CVE-2010-5141); in 0.3.6 OP_RETURN makes the script fail,
  while the two scripts are still joined.
- 0.3.7 and later: VerifyScript runs scriptSig, then scriptPubKey on the
  stack it left, and checks the top of the stack.
Sources: script.cpp of the tags v0.3.3, v0.3.6, v0.3.7 on github.com/bitcoin/bitcoin.
"""

VALID_SIG = 'sig-by-owner'   # the stub OP_CHECKSIG accepts only this


def run(script, stack, return_jumps):
    pc = 0
    while pc < len(script):
        op = script[pc]
        if op == 'OP_1':
            stack.append(1)
        elif op == 'OP_RETURN':
            if return_jumps:
                pc = len(script)          # 0.3.4 and earlier: skip to the end
                continue
            return False                  # 0.3.6 and later: fail
        elif op == 'OP_CODESEPARATOR':
            pass
        elif op == 'OP_CHECKSIG':
            pub, sig = stack.pop(), stack.pop()
            stack.append(1 if (sig, pub) == (VALID_SIG, 'owner-pubkey') else 0)
        else:
            stack.append(op)              # data push
        pc += 1
    return True


def joined(sig, pub, return_jumps):
    stack = []
    ok = run(sig + ['OP_CODESEPARATOR'] + pub, stack, return_jumps)
    return ok and bool(stack) and stack[-1] == 1


def separate(sig, pub):
    stack = []
    if not run(sig, stack, return_jumps=False):
        return False
    if not run(pub, stack, return_jumps=False):
        return False
    return bool(stack) and stack[-1] == 1


script_pubkey = ['owner-pubkey', 'OP_CHECKSIG']     # P2PK: <pubkey> OP_CHECKSIG
spends = {
    'owner': [VALID_SIG],
    'attacker': ['OP_1', 'OP_RETURN'],
}
print(f'{"scriptSig":<24}{"<=0.3.4 joined":>16}{"0.3.6 joined":>14}{">=0.3.7 separate":>18}')
for who, sig in spends.items():
    row = [joined(sig, script_pubkey, True), joined(sig, script_pubkey, False), separate(sig, script_pubkey)]
    print(f'{who + ": " + " ".join(sig):<24}' + ''.join(f'{str(v):>16}' if i == 0 else f'{str(v):>14}' if i == 1 else f'{str(v):>18}' for i, v in enumerate(row)))
