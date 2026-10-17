SJGAM M68 — firmware teardown, as a web page

index.html is a technical write-up of what we found on the SD card of a retail
SJGAM M68 (build M68 V1.0.0, 22 January 2026): hardware identification, the
boot path, how the menu is assembled, the game database schema, the missing
emulator cores, and the encrypted /etc/webster blob.

Deployed to https://simonccc.github.io/m68/ by .github/workflows/pages.yml on
any push that touches this directory.

Layout
  index.html                        the page; styles inline, no dependencies
  assets/product-*.jpg              manufacturer product photographs
  research/manufacturer-source.html snapshot of the SJGAM M66 listing

Images are referenced rather than embedded, so open index.html from this
directory, not on its own. (It previously inlined them as data URIs and was
6.4 MB; it is now 32 KB.)

Scope: one unit, one build. Sections 01-08 are first-hand, read from the card
or disassembled from /usr/bin/game. The product photographs and any M66
specification are manufacturer-published and were not independently verified.
SJGAM's own site documents no M68 — the page the device is sold under
describes the M66, which is a different platform.

Supporting notes and tooling are in the parent repository.
