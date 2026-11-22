// Sunday 22 November 2026, the world's news of that day, in one picture.
// The picture is entry.png, drawn by tools/build_entry.py and committed beside
// this program. The grader reads exactly the bytes at /output/entry.png, so this
// program puts those bytes there and writes nothing else, after checking that
// what it is about to copy is a whole PNG the gate can take.
//
//   mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const LIMIT_BYTES = 1048576;
const LIMIT_EDGE = 1024;

const here = dirname(fileURLToPath(import.meta.url));
const outDir = process.env.MAKEFUN_OUTPUT_DIR ?? "/output";
const picture = readFileSync(join(here, "entry.png"));

function inspect(png: Buffer): string {
  const signature = [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  if (png.length < 33 || !signature.every((byte, i) => png[i] === byte)) {
    throw new Error("entry.png is not a PNG");
  }
  if (png.readUInt32BE(8) !== 13 || png.subarray(12, 16).toString("latin1") !== "IHDR") {
    throw new Error("entry.png has no IHDR header the gate can read");
  }
  const width = png.readUInt32BE(16);
  const height = png.readUInt32BE(20);
  const tail = png.subarray(png.length - 12);
  if (tail.readUInt32BE(0) !== 0 || tail.subarray(4, 8).toString("latin1") !== "IEND") {
    throw new Error("entry.png does not end with a whole IEND chunk: the file is cut short");
  }
  if (width > LIMIT_EDGE || height > LIMIT_EDGE) {
    throw new Error(`entry.png is ${width}x${height}, over the ${LIMIT_EDGE} pixel edge`);
  }
  if (png.length > LIMIT_BYTES) {
    throw new Error(`entry.png is ${png.length} bytes, over the ${LIMIT_BYTES} byte limit`);
  }
  return `${width}x${height}, ${png.length} bytes`;
}

const shape = inspect(picture);
mkdirSync(outDir, { recursive: true });
const target = join(outDir, "entry.png");
writeFileSync(target, picture);

const written = readFileSync(target);
if (!written.equals(picture)) {
  throw new Error("the bytes written do not match the picture they came from");
}
console.log(`entry.png ${shape} -> ${target}`);
