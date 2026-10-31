// Run with: node --test scripts/check_game_pick.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../assets/js/game-pick.js', import.meta.url), 'utf8');
for (const [random, expected] of [[0, 0], [0.999, 1]]) {
  test(`select game ${expected} and leave exactly one playable card`, () => {
    const cards = [{ hidden: false }, { hidden: true }];
    runInNewContext(source, {
      document: { querySelectorAll: () => [{ querySelectorAll: () => cards }] },
      Math: { random: () => random, floor: Math.floor },
    });
    assert.deepEqual(cards.map(card => card.hidden), [expected !== 0, expected !== 1]);
  });
}
