import { bold, cyan, dim, gray, green } from "./colors";

const isTTY = typeof process.stdin.setRawMode === "function";

/**
 * Interactive select prompt using raw stdin.
 * Falls back to first option in non-TTY environments.
 */
export async function select<T>(opts: {
  message: string;
  options: Array<{ label: string; value: T; hint?: string }>;
}): Promise<T> {
  const { message, options } = opts;
  if (options.length === 0) throw new Error("No options");
  if (options.length === 1) return options[0].value;

  // Non-TTY: auto-select first option
  if (!isTTY) {
    console.log(`${bold(cyan("? "))}${bold(message)} ${green(options[0].label)}`);
    return options[0].value;
  }

  let cursor = 0;
  let renderedLines = 0;

  const countLines = (text: string): number => {
    const cols = process.stdout.columns || 80;
    return text.split("\n").reduce((sum, line) => {
      // Strip ANSI codes for accurate length
      const stripped = line.replace(/\x1b\[[0-9;]*m/g, "");
      return sum + Math.max(1, Math.ceil(stripped.length / cols));
    }, 0);
  };

  const render = () => {
    // Clear previous render
    if (renderedLines > 0) {
      process.stdout.write(`\x1b[${renderedLines}A\x1b[J`);
    }
    const lines: string[] = [];
    lines.push(bold(cyan("? ")) + bold(message));
    for (let i = 0; i < options.length; i++) {
      const prefix = i === cursor ? green("> ") : "  ";
      const label = i === cursor ? bold(options[i].label) : options[i].label;
      const hint = options[i].hint ? dim(` ${options[i].hint}`) : "";
      lines.push(`${prefix}${label}${hint}`);
    }
    const output = lines.join("\n");
    console.log(output);
    renderedLines = countLines(output);
  };

  // Initial render
  render();

  return new Promise<T>((resolve) => {
    const stdin = process.stdin;
    stdin.setRawMode(true);
    stdin.resume();

    const onData = (data: Buffer) => {
      const key = data.toString();

      if (key === "\x1b[A" || key === "k") {
        // up
        cursor = (cursor - 1 + options.length) % options.length;
        render();
      } else if (key === "\x1b[B" || key === "j") {
        // down
        cursor = (cursor + 1) % options.length;
        render();
      } else if (key === "\r" || key === "\n") {
        // enter
        cleanup();
        resolve(options[cursor].value);
      } else if (key === "\x03" || key === "q") {
        // ctrl-c or q
        cleanup();
        process.exit(130);
      }
    };

    const cleanup = () => {
      stdin.removeListener("data", onData);
      stdin.setRawMode(false);
      stdin.pause();
    };

    stdin.on("data", onData);
  });
}

/**
 * Simple confirmation prompt.
 * Falls back to default value in non-TTY.
 */
export async function confirm(message: string, defaultValue = false): Promise<boolean> {
  const hint = defaultValue ? "[Y/n]" : "[y/N]";

  if (!isTTY) {
    console.log(`${bold(cyan("? "))}${bold(message)} ${gray(hint)} ${defaultValue ? "yes" : "no"}`);
    return defaultValue;
  }

  process.stdout.write(`${bold(cyan("? "))}${bold(message)} ${gray(hint)} `);

  return new Promise<boolean>((resolve) => {
    const stdin = process.stdin;
    stdin.setRawMode(true);
    stdin.resume();

    const onData = (data: Buffer) => {
      const key = data.toString().toLowerCase();
      stdin.removeListener("data", onData);
      stdin.setRawMode(false);
      stdin.pause();

      if (key === "y") {
        console.log("yes");
        resolve(true);
      } else if (key === "n") {
        console.log("no");
        resolve(false);
      } else if (key === "\r" || key === "\n") {
        console.log(defaultValue ? "yes" : "no");
        resolve(defaultValue);
      } else if (key === "\x03") {
        console.log();
        process.exit(130);
      } else {
        console.log(defaultValue ? "yes" : "no");
        resolve(defaultValue);
      }
    };

    stdin.on("data", onData);
  });
}

/**
 * Simple text input prompt.
 */
export async function input(message: string, placeholder?: string): Promise<string> {
  const hint = placeholder ? gray(` (${placeholder})`) : "";
  process.stdout.write(`${bold(cyan("? "))}${bold(message)}${hint} `);

  return new Promise<string>((resolve) => {
    const rl = require("readline").createInterface({
      input: process.stdin,
      output: process.stdout,
    });
    // Read one line then close
    rl.on("line", (line: string) => {
      rl.close();
      resolve(line.trim() || placeholder || "");
    });
  });
}

/**
 * Spinner for async operations.
 */
export function spinner(message: string) {
  const frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  let i = 0;
  let text = message;

  if (!isTTY) {
    console.log(`  ${text}`);
    return {
      update(msg: string) { console.log(`  ${msg}`); },
      stop(finalMsg?: string) { if (finalMsg) console.log(finalMsg); },
    };
  }

  const id = setInterval(() => {
    process.stdout.write(`\r${cyan(frames[i % frames.length])} ${text}`);
    i++;
  }, 80);

  return {
    update(msg: string) {
      text = msg;
    },
    stop(finalMsg?: string) {
      clearInterval(id);
      process.stdout.write("\r\x1b[K");
      if (finalMsg) console.log(finalMsg);
    },
  };
}
