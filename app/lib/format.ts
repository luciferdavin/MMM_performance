export function formatCurrency(value: number): string {
  const abs = Math.abs(value);
  const sign = value < 0 ? '-' : '';
  if (abs >= 1_000_000) {
    const millions = (abs / 1_000_000).toFixed(2).replace(/\.00$/, '');
    return `${sign}$${millions}M`;
  }
  if (abs >= 1_000) {
    const thousands = (abs / 1_000).toFixed(1).replace(/\.0$/, '');
    return `${sign}$${thousands}k`;
  }
  return `${sign}$${abs.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

export function formatCurrencyExact(value: number): string {
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function formatNumber(value: number): string {
  return value.toLocaleString('en-US');
}

export function formatRoas(value: number): string {
  return `${value.toFixed(1)}x`;
}

export function formatDate(value: string | Date): string {
  const date = typeof value === 'string' ? new Date(value) : value;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatRelative(value: string | Date): string {
  const date = typeof value === 'string' ? new Date(value) : value;
  const seconds = Math.round((date.getTime() - Date.now()) / 1000);
  const abs = Math.abs(seconds);
  const formatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  if (abs < 60) return formatter.format(Math.round(seconds), 'second');
  if (abs < 3_600) return formatter.format(Math.round(seconds / 60), 'minute');
  if (abs < 86_400) return formatter.format(Math.round(seconds / 3_600), 'hour');
  if (abs < 604_800) return formatter.format(Math.round(seconds / 86_400), 'day');
  return formatDate(date);
}
