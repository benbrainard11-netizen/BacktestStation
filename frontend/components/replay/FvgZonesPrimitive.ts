// FVG zone rectangles drawn as a lightweight-charts custom primitive.
//
// Each zone occupies a horizontal band [low..high] in price and a temporal
// span from `createdAt` to either `fillTime` or the chart's right edge.
// We render a filled rectangle with low alpha plus a 1px border so the
// reviewer can see "did this trade enter inside an unfilled FVG?" at a
// glance. The reuse of the chart's pixel-coordinate API keeps the band
// pinned to the right price even as the user pans/zooms.
import type {
  IChartApi,
  IPrimitivePaneRenderer,
  IPrimitivePaneView,
  ISeriesApi,
  ISeriesPrimitive,
  SeriesType,
  Time,
} from "lightweight-charts";

export interface FvgZoneInput {
  direction: "BULLISH" | "BEARISH" | string;
  low: number;
  high: number;
  /** Bar-aligned epoch second when the gap was created. */
  createdAtSec: number;
  /** Bar-aligned epoch second of fill, or null if still unfilled. */
  fillTimeSec: number | null;
}

const FILL_BULLISH = "rgba(34, 197, 94, 0.10)"; // emerald-500 @ 10%
const FILL_BEARISH = "rgba(239, 68, 68, 0.10)"; // red-500 @ 10%
const STROKE_BULLISH = "rgba(34, 197, 94, 0.50)";
const STROKE_BEARISH = "rgba(239, 68, 68, 0.50)";
const FILLED_FILL_OPACITY = 0.04;

class FvgZonesRenderer implements IPrimitivePaneRenderer {
  constructor(
    private readonly chart: IChartApi,
    private readonly series: ISeriesApi<SeriesType>,
    private readonly zones: FvgZoneInput[],
  ) {}

  draw(target: Parameters<IPrimitivePaneRenderer["draw"]>[0]): void {
    target.useBitmapCoordinateSpace((scope) => {
      const ctx = scope.context;
      const { horizontalPixelRatio: hpr, verticalPixelRatio: vpr } = scope;
      const timeScale = this.chart.timeScale();

      const visible = timeScale.getVisibleRange();
      const rightEdgeSec =
        visible !== null ? Number(visible.to) : null;

      for (const z of this.zones) {
        const x1 = timeScale.timeToCoordinate(z.createdAtSec as Time);
        if (x1 === null) continue;

        const fillSec =
          z.fillTimeSec ??
          rightEdgeSec ??
          // Fallback: extend the band ~4hrs to the right of created-at.
          z.createdAtSec + 4 * 60 * 60;
        const x2Raw = timeScale.timeToCoordinate(fillSec as Time);
        const x2 = x2Raw === null ? null : x2Raw;
        if (x2 === null) continue;

        const yHigh = this.series.priceToCoordinate(z.high);
        const yLow = this.series.priceToCoordinate(z.low);
        if (yHigh === null || yLow === null) continue;

        const left = Math.min(x1, x2) * hpr;
        const right = Math.max(x1, x2) * hpr;
        const top = Math.min(yHigh, yLow) * vpr;
        const bottom = Math.max(yHigh, yLow) * vpr;

        const isBull = z.direction === "BULLISH";
        const isFilled = z.fillTimeSec !== null;
        const baseFill = isBull ? FILL_BULLISH : FILL_BEARISH;
        const stroke = isBull ? STROKE_BULLISH : STROKE_BEARISH;
        // Filled zones: render at lower opacity so unfilled gaps pop.
        ctx.fillStyle = isFilled
          ? rgbaWithAlpha(baseFill, FILLED_FILL_OPACITY)
          : baseFill;
        ctx.fillRect(left, top, right - left, bottom - top);

        ctx.strokeStyle = stroke;
        ctx.lineWidth = Math.max(1, Math.round(hpr));
        ctx.strokeRect(left, top, right - left, bottom - top);
      }
    });
  }
}

function rgbaWithAlpha(rgba: string, alpha: number): string {
  // Replace the alpha component of an rgba(...) string.
  return rgba.replace(/rgba\(([^)]+)\)/, (_, body) => {
    const parts = body.split(",").map((s: string) => s.trim());
    if (parts.length < 3) return rgba;
    return `rgba(${parts[0]}, ${parts[1]}, ${parts[2]}, ${alpha})`;
  });
}

class FvgZonesPaneView implements IPrimitivePaneView {
  constructor(
    private readonly chart: IChartApi,
    private readonly series: ISeriesApi<SeriesType>,
    private zones: FvgZoneInput[],
  ) {}

  setZones(zones: FvgZoneInput[]): void {
    this.zones = zones;
  }

  zOrder(): "bottom" | "normal" | "top" {
    // "bottom" so the candles draw on top — the band is context, not focus.
    return "bottom";
  }

  renderer(): IPrimitivePaneRenderer {
    return new FvgZonesRenderer(this.chart, this.series, this.zones);
  }
}

/**
 * A series primitive that draws FVG bands behind the candles. Construct
 * once, attach to a candlestick series, and call setZones() whenever the
 * payload changes — the chart will repaint on its own.
 */
export class FvgZonesPrimitive implements ISeriesPrimitive<Time> {
  private paneView: FvgZonesPaneView | null = null;
  private chart: IChartApi | null = null;
  private series: ISeriesApi<SeriesType> | null = null;
  private zones: FvgZoneInput[] = [];
  private requestUpdate: (() => void) | null = null;

  attached(param: {
    chart: IChartApi;
    series: ISeriesApi<SeriesType>;
    requestUpdate: () => void;
  }): void {
    this.chart = param.chart;
    this.series = param.series;
    this.requestUpdate = param.requestUpdate;
    this.paneView = new FvgZonesPaneView(param.chart, param.series, this.zones);
    param.requestUpdate();
  }

  detached(): void {
    this.paneView = null;
    this.chart = null;
    this.series = null;
    this.requestUpdate = null;
  }

  setZones(zones: FvgZoneInput[]): void {
    this.zones = zones;
    if (this.paneView) this.paneView.setZones(zones);
    this.requestUpdate?.();
  }

  paneViews(): readonly IPrimitivePaneView[] {
    return this.paneView ? [this.paneView] : [];
  }

  updateAllViews(): void {
    if (this.paneView) this.paneView.setZones(this.zones);
  }
}
