const CHANNEL_COLORS: Record<string, string> = {
  meta: '#1877F2',
  google_ads: '#EA4335',
  tiktok: '#111111',
  shopify_revenue: '#96BF48',
  organic: '#14B8A6',
  tv: '#8B5CF6',
  radio: '#F59E0B',
};

const FALLBACK_CYCLE = ['#4F46E5', '#0EA5E9', '#10B981', '#F97316', '#EC4899', '#64748B'];

export function channelColor(channel: string, index = 0): string {
  return CHANNEL_COLORS[channel] ?? FALLBACK_CYCLE[index % FALLBACK_CYCLE.length];
}

export const CHANNEL_LABELS: Record<string, string> = {
  meta: 'Meta',
  google_ads: 'Google Ads',
  tiktok: 'TikTok',
  shopify_revenue: 'Shopify Revenue',
  organic: 'Organic',
  tv: 'TV',
  radio: 'Radio',
};

export function channelLabel(channel: string): string {
  return CHANNEL_LABELS[channel] ?? channel;
}
