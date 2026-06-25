// InSyncMarketState - Quantower chart overlay bridging the InSync :9100 backend.
// No model porting, no extra feed, no licensing concern (your data, your box).
//
//   GET {BackendUrl}/api/monitor/options-levels
//       futures[DataSymbol].levels[] {kind, price, title, note}  -> horizontal lines
//       futures[DataSymbol].future_px                            -> anchor for the move band
//       kind: call_wall|put_wall|gex_wall_pos|gex_wall_neg|zero_gamma|max_pain
//       (level.price already basis-mapped to the futures -> draws straight on NQ/ES)
//   GET {BackendUrl}/api/monitor/market-state?symbol={MarketStateSymbol}
//       tiles.move_size  {status, regime, regime_range_t}        -> expected-range band
//       tiles.big_player {source, big_bid{px,size}, big_ask{px,size}} -> iceberg lines
//
// Inputs: Backend URL / Data symbol (NQ.c.0) / Market-state symbol (NQ) / Tick size.

using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using TradingPlatform.BusinessLayer;

namespace InSyncMarketState
{
    public class InSyncMarketState : Indicator
    {
        [InputParameter("Backend URL", 0)]
        public string BackendUrl = "http://127.0.0.1:9100";

        [InputParameter("Data symbol (options-levels key)", 1)]
        public string DataSymbol = "NQ.c.0";

        [InputParameter("Market-state symbol", 2)]
        public string MarketStateSymbol = "NQ";

        [InputParameter("Tick size", 3, 0.01, 100.0, 0.01, 2)]
        public double TickSize = 0.25;

        [InputParameter("Poll seconds", 4, 5, 300, 1, 0)]
        public int PollSeconds = 20;

        [InputParameter("Show labels", 5)]
        public bool ShowLabels = true;

        [InputParameter("Show move-size band", 6)]
        public bool ShowMoveBand = true;

        [InputParameter("Show big-player levels", 7)]
        public bool ShowBigPlayer = true;

        private static readonly HttpClient Http = new HttpClient { Timeout = TimeSpan.FromSeconds(8) };
        private Timer _timer;
        private volatile Snapshot _snap;
        private readonly Font _font = new Font("Segoe UI", 8f);

        public InSyncMarketState() : base()
        {
            Name = "InSync Market State";
            SeparateWindow = false;
        }

        protected override void OnInit()
        {
            _timer = new Timer(async _ => await FetchAsync(), null, 0, Math.Max(5, PollSeconds) * 1000);
        }

        protected override void OnClear()
        {
            _timer?.Dispose();
            _timer = null;
        }

        private static string Str(JsonElement e, string prop, string dflt = null)
            => e.TryGetProperty(prop, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : dflt;
        private static double? Dbl(JsonElement e, string prop)
            => e.TryGetProperty(prop, out var v) && v.TryGetDouble(out var d) ? d : (double?)null;

        private async Task FetchAsync()
        {
            var snap = new Snapshot();
            try
            {
                string json = await Http.GetStringAsync(BackendUrl.TrimEnd('/') + "/api/monitor/options-levels").ConfigureAwait(false);
                using JsonDocument doc = JsonDocument.Parse(json);
                var root = doc.RootElement;
                snap.OptStatus = Str(root, "status", "");
                if (root.TryGetProperty("futures", out var futs) && futs.TryGetProperty(DataSymbol, out var fut))
                {
                    snap.FuturePx = Dbl(fut, "future_px") ?? Dbl(fut, "spot");
                    if (fut.TryGetProperty("levels", out var lvls) && lvls.ValueKind == JsonValueKind.Array)
                        foreach (var lv in lvls.EnumerateArray())
                        {
                            double? px = Dbl(lv, "price");
                            if (px == null) continue;
                            string kind = Str(lv, "kind", "");
                            string title = Str(lv, "title", kind);
                            string note = Str(lv, "note");
                            snap.Lines.Add(new LevelLine { Price = px.Value, Kind = kind, Label = string.IsNullOrEmpty(note) ? title : title + " " + note });
                        }
                }
            }
            catch { snap.OptStatus = "offline"; }

            try
            {
                string url = BackendUrl.TrimEnd('/') + "/api/monitor/market-state?symbol=" + Uri.EscapeDataString(MarketStateSymbol);
                string json = await Http.GetStringAsync(url).ConfigureAwait(false);
                using JsonDocument doc = JsonDocument.Parse(json);
                if (doc.RootElement.TryGetProperty("tiles", out var tiles))
                {
                    if (tiles.TryGetProperty("move_size", out var mv))
                    {
                        snap.MoveStatus = Str(mv, "status", "");
                        snap.MoveRegime = Str(mv, "regime", "");
                        snap.MoveRangeT = Dbl(mv, "regime_range_t");
                    }
                    if (tiles.TryGetProperty("big_player", out var bp))
                    {
                        snap.BigSource = Str(bp, "source");
                        if (bp.TryGetProperty("big_bid", out var bb) && bb.ValueKind == JsonValueKind.Object)
                        { snap.BigBidPx = Dbl(bb, "px"); snap.BigBidSize = Dbl(bb, "size"); }
                        if (bp.TryGetProperty("big_ask", out var ba) && ba.ValueKind == JsonValueKind.Object)
                        { snap.BigAskPx = Dbl(ba, "px"); snap.BigAskSize = Dbl(ba, "size"); }
                    }
                }
            }
            catch { }

            _snap = snap;
        }

        public override void OnPaintChart(PaintChartEventArgs args)
        {
            var snap = _snap;
            if (snap == null) return;
            var windows = this.CurrentChart?.Windows;
            if (windows == null || args.WindowIndex < 0 || args.WindowIndex >= windows.Count()) return;
            var conv = windows[args.WindowIndex].CoordinatesConverter;
            if (conv == null) return;
            Graphics gr = args.Graphics;
            Rectangle rect = args.Rectangle;
            int Y(double price) { try { return (int)conv.GetChartY(price); } catch { return int.MinValue; } }

            foreach (var ln in snap.Lines)
            {
                int y = Y(ln.Price);
                if (y == int.MinValue || y < rect.Top - 2 || y > rect.Bottom + 2) continue;
                var (col, dash) = StyleFor(ln.Kind);
                using (var pen = new Pen(col, 1f) { DashStyle = dash }) gr.DrawLine(pen, rect.Left, y, rect.Right, y);
                if (ShowLabels && !string.IsNullOrEmpty(ln.Label))
                    using (var br = new SolidBrush(col)) gr.DrawString(ln.Label + "  " + ln.Price.ToString("0.##"), _font, br, rect.Left + 4, y - 13);
            }

            if (ShowMoveBand && snap.MoveStatus == "live" && snap.MoveRangeT.HasValue && snap.FuturePx.HasValue && TickSize > 0)
            {
                double half = snap.MoveRangeT.Value * TickSize / 2.0;
                int yHi = Y(snap.FuturePx.Value + half), yLo = Y(snap.FuturePx.Value - half);
                if (yHi != int.MinValue && yLo != int.MinValue)
                {
                    Color c = snap.MoveRegime == "hi" ? ColorTranslator.FromHtml("#f87171")
                            : snap.MoveRegime == "mid" ? ColorTranslator.FromHtml("#eab308")
                            : ColorTranslator.FromHtml("#94a3b8");
                    using (var fill = new SolidBrush(Color.FromArgb(28, c)))
                        gr.FillRectangle(fill, rect.Left, Math.Min(yHi, yLo), rect.Width, Math.Abs(yLo - yHi));
                    using (var pen = new Pen(c, 1f) { DashStyle = DashStyle.Dash })
                    { gr.DrawLine(pen, rect.Left, yHi, rect.Right, yHi); gr.DrawLine(pen, rect.Left, yLo, rect.Right, yLo); }
                    if (ShowLabels)
                        using (var br = new SolidBrush(c))
                            gr.DrawString("exp move " + snap.MoveRegime + " +/-" + Math.Round(half, 2), _font, br, rect.Left + 4, yHi - 13);
                }
            }

            if (ShowBigPlayer)
            {
                DrawIceberg(gr, rect, Y, snap.BigBidPx, snap.BigBidSize, ColorTranslator.FromHtml("#34d399"), "iceberg bid");
                DrawIceberg(gr, rect, Y, snap.BigAskPx, snap.BigAskSize, ColorTranslator.FromHtml("#fb7185"), "iceberg ask");
            }

            var panel = new List<string> { "InSync market state" };
            panel.Add("gamma: " + snap.Lines.Count + " levels (" + snap.OptStatus + ")");
            if (snap.MoveStatus == "live" && snap.MoveRangeT.HasValue)
                panel.Add("move: " + snap.MoveRegime + "  +/-" + Math.Round((snap.MoveRangeT.Value * TickSize) / 2.0, 1));
            if (!string.IsNullOrEmpty(snap.BigSource))
                panel.Add("iceberg: " + snap.BigSource);
            DrawPanel(gr, rect, panel);
        }

        private void DrawIceberg(Graphics gr, Rectangle rect, Func<double, int> Y, double? px, double? size, Color col, string label)
        {
            if (!px.HasValue) return;
            int y = Y(px.Value);
            if (y == int.MinValue || y < rect.Top - 2 || y > rect.Bottom + 2) return;
            using (var pen = new Pen(col, 1.5f) { DashStyle = DashStyle.Dash }) gr.DrawLine(pen, rect.Left, y, rect.Right, y);
            if (ShowLabels)
                using (var br = new SolidBrush(col))
                    gr.DrawString(label + (size.HasValue ? "  " + size.Value.ToString("0") : "") + "  " + px.Value.ToString("0.##"), _font, br, rect.Left + 4, y - 13);
        }

        private void DrawPanel(Graphics gr, Rectangle rect, List<string> lines)
        {
            float w = 0, h = 0;
            foreach (var s in lines) { var sz = gr.MeasureString(s, _font); if (sz.Width > w) w = sz.Width; h += sz.Height; }
            using (var bg = new SolidBrush(Color.FromArgb(150, 0, 0, 0)))
                gr.FillRectangle(bg, rect.Left + 4, rect.Top + 4, w + 10, h + 6);
            float yy = rect.Top + 6;
            using (var fg = new SolidBrush(Color.FromArgb(225, 226, 232, 240)))
                foreach (var s in lines) { gr.DrawString(s, _font, fg, rect.Left + 8, yy); yy += gr.MeasureString(s, _font).Height; }
        }

        private static (Color, DashStyle) StyleFor(string kind)
        {
            switch (kind)
            {
                case "call_wall":    return (ColorTranslator.FromHtml("#38bdf8"), DashStyle.Dash);
                case "put_wall":     return (ColorTranslator.FromHtml("#f59e0b"), DashStyle.Dash);
                case "gex_wall_pos": return (ColorTranslator.FromHtml("#a78bfa"), DashStyle.Solid);
                case "gex_wall_neg": return (ColorTranslator.FromHtml("#f472b6"), DashStyle.Solid);
                case "zero_gamma":   return (ColorTranslator.FromHtml("#e879f9"), DashStyle.Dot);
                case "max_pain":     return (ColorTranslator.FromHtml("#94a3b8"), DashStyle.Dot);
                default:             return (Color.FromArgb(148, 163, 184), DashStyle.Dot);
            }
        }

        private sealed class Snapshot
        {
            public List<LevelLine> Lines = new List<LevelLine>();
            public double? FuturePx;
            public string OptStatus = "";
            public string MoveStatus = "", MoveRegime = "";
            public double? MoveRangeT;
            public double? BigBidPx, BigBidSize, BigAskPx, BigAskSize;
            public string BigSource;
        }

        private sealed class LevelLine { public double Price; public string Kind; public string Label; }
    }
}
