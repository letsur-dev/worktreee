import { writeFileSync } from "fs";

/**
 * Signal the shell wrapper to cd into a directory.
 * Uses __WT_CD_FILE__ env (tmpfile) if available, otherwise falls back to stdout marker.
 */
export function requestCd(path: string) {
  const cdFile = process.env.__WT_CD_FILE__;
  if (cdFile) {
    writeFileSync(cdFile, path, "utf-8");
  } else {
    // Fallback for direct invocation without shell wrapper
    console.log(`__WT_CD__:${path}`);
  }
}
