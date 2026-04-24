export function formatUSD(value: number, digits = 2): string {
  return value.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatUSDCompact(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1_000) {
    return `$${(value / 1_000).toFixed(0)}K`;
  }
  return formatUSD(value);
}

export function formatNumber(value: number, digits = 0): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatSigned(value: number, digits = 2): string {
  const fixed = Math.abs(value).toFixed(digits);
  if (value > 0) return `+${fixed}`;
  if (value < 0) return `-${fixed}`;
  return fixed;
}

export function formatPercent(value: number, digits = 2): string {
  return `${value.toFixed(digits)}%`;
}

export function formatSignedPercent(value: number, digits = 2): string {
  const fixed = Math.abs(value).toFixed(digits);
  if (value > 0) return `+${fixed}%`;
  if (value < 0) return `-${fixed}%`;
  return `${fixed}%`;
}

export function toneFor(value: number): "positive" | "negative" | "neutral" {
  if (value > 0) return "positive";
  if (value < 0) return "negative";
  return "neutral";
}
