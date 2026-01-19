import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Utility function to merge Tailwind CSS classes and handle class conflicts.
 * It combines the functionality of clsx (for conditional classes)
 * and tailwind-merge (for resolving conflicting Tailwind classes).
 */
export function cx(...inputs: ClassValue[]) {
  return twMerge(clsx(...inputs));
}

/**
 * identity function to help the Tailwind CSS VS Code extension (and Prettier plugin)
 * sort classes within nested objects.
 * https://github.com/tailwindlabs/tailwindcss-intellisense/issues/227#issuecomment-1139895799
 */
export function sortCx<
  T extends Record<
    string,
    | string
    | number
    | Record<string, string | number | Record<string, string | number>>
  >,
>(classes: T): T {
  return classes;
}
