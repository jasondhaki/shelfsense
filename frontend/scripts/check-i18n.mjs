// Checks every Bengali string keeps exactly the {placeholders} of its English key.
// (Missing keys are caught by `npm run typecheck`: t() only accepts keys present in BN.)
import { readFileSync } from 'node:fs'

const src = readFileSync(new URL('../src/lib/bn.ts', import.meta.url), 'utf8')
const pairs = [...src.matchAll(/^\s*(?:'((?:[^'\\]|\\.)*)'|(\w+)):\s*\n?\s*'((?:[^'\\]|\\.)*)',?$/gm)]
const holes = (s) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort().join(',')
let bad = 0
for (const [, quoted, bare, bn] of pairs) {
  const en = quoted ?? bare
  if (holes(en) !== holes(bn)) {
    console.error(`placeholder mismatch: ${en} → ${bn}`)
    bad++
  }
}
if (pairs.length < 400) {
  console.error(`only parsed ${pairs.length} entries — check the regex against bn.ts`)
  bad++
}
console.log(`${pairs.length} entries checked`)
process.exit(bad ? 1 : 0)
