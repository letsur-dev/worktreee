const enabled = process.env.NO_COLOR === undefined && process.stdout.isTTY !== false;

const code = (open: number, close: number) => {
  if (!enabled) return (s: string) => s;
  return (s: string) => `\x1b[${open}m${s}\x1b[${close}m`;
};

export const bold = code(1, 22);
export const dim = code(2, 22);
export const italic = code(3, 23);
export const underline = code(4, 24);
export const red = code(31, 39);
export const green = code(32, 39);
export const yellow = code(33, 39);
export const blue = code(34, 39);
export const magenta = code(35, 39);
export const cyan = code(36, 39);
export const gray = code(90, 39);
export const white = code(37, 39);

export const bgRed = code(41, 49);
export const bgGreen = code(42, 49);
export const bgYellow = code(43, 49);
export const bgBlue = code(44, 49);

export const symbols = {
  check: "\u2714",
  cross: "\u2718",
  arrow: "\u276f",
  dot: "\u25cf",
  dash: "\u2500",
  ellipsis: "\u2026",
  warning: "\u26a0",
  info: "\u2139",
  spinner: ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"],
};
