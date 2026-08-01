export interface CurvePoint {
  spend: number;
  revenue: number;
}

/**
 * Hill saturation curve used to render a placeholder response curve:
 * revenue(spend) = peak * spend^s / (k^s + spend^s)
 */
export function responseCurve(
  spendMax: number,
  peakRevenue: number,
  k: number,
  s: number,
  points = 20,
): CurvePoint[] {
  const result: CurvePoint[] = [];
  for (let i = 0; i <= points; i += 1) {
    const spend = (spendMax * i) / points;
    const revenue = (peakRevenue * Math.pow(spend, s)) / (Math.pow(k, s) + Math.pow(spend, s));
    result.push({ spend, revenue });
  }
  return result;
}
