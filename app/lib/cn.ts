export type ClassValue = string | number | null | false | undefined;

export function cn(...classes: ClassValue[]): string {
  return classes.filter((c) => Boolean(c)).join(' ');
}
