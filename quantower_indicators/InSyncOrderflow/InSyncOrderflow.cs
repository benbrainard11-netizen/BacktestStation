// InSync Orderflow - custom Quantower indicator that reads the platform's OWN
// Rithmic L2 + trades (no 2nd login, no harvester) to flag icebergs / absorption
// / imbalance / aggressive prints, AND overlays the InSync backtested EXHAUSTION
// model from the :9100 backend:
//   - the CURRENT reversal read, always shown while live (faint watch-line + odds,
//     bold dashed line when it actually fires)
//   - EVERY fire today as a marker at the swept extreme (down-arrow above a faded
//     high = fade-short; up-arrow below a faded low = fade-long)
//   - the day's REGIME banner (calm/mid/wild + expected range)
//
//   L2:     Symbol.DepthOfMarket.GetDepthOfMarketAggregatedCollections(...)  (polled on a timer)
//   trades: Symbol.NewLast -> Last{Price,Size,AggressorFlag(Buy/Sell/None)}   (background thread)
//   model:  GET {BackendUrl}/api/monitor/market-state?symbol={Sym}     -> tiles.reversal + tiles.move_size
//           GET {BackendUrl}/api/monitor/reversal-history?symbol={Sym} -> events[] (every fire today)
//   draw:   OnPaintChart -> CoordinatesConverter.GetChartY(price) / GetChartX(time)

using System;
using System.Collections.Generic;
using System.Linq;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Net.Http;
using System.Text.Json;
using System.Threading;
using TradingPlatform.BusinessLayer;

namespace InSyncOrderflow
{
    public class InSyncOrderflow : Indicator
    {
        [InputParameter("Backend URL (exhaustion)", 0)]
        public string BackendUrl = "http://127.0.0.1:9100";
        [InputParameter("Market-state symbol", 1)]
        public string MarketStateSymbol = "NQ";
        [InputParameter("DOM levels to scan", 2, 5, 200, 1, 0)]
        public int DomLevels = 50;
        [InputParameter("Wall size (contracts)", 3, 1, 1000000, 1, 0)]
        public double WallSize = 25;
        [InputParameter("Iceberg multiple (recent vol / shown)", 4, 1.0, 50.0, 0.5, 1)]
        public double IcebergMult = 3.0;
        [InputParameter("Iceberg min recent volume", 11, 1, 100000, 1, 0)]
        public double IcebergMinVol = 30;
        [InputParameter("Big print size (contracts)", 5, 1, 1000000, 1, 0)]
        public double BigPrintSize = 10;
        [InputParameter("Imbalance levels", 6, 1, 50, 1, 0)]
        public int ImbalanceLevels = 10;
        [InputParameter("Show walls / icebergs / absorption", 7)]
        public bool ShowWalls = true;
        [InputParameter("Show plain walls (static resting size)", 24)]
        public bool ShowPlainWalls = false;   // OFF by default -> only absorption/iceberg EVENTS show, not every big resting level
        [InputParameter("Show aggressive prints", 8)]
        public bool ShowPrints = true;
        [InputParameter("Trade bubbles (vs triangles)", 25)]
        public bool BubbleMode = true;   // circles sized by trade size = classic order-flow flow view
        [InputParameter("Max bubbles", 26, 5, 1000, 5, 0)]
        public int MaxBubbles = 80;      // cap on how many bubbles on screen (biggest kept)
        [InputParameter("Show market state panel", 27)]
        public bool ShowMarketState = true;   // its OWN switch (not tied to the old regime-banner toggle)
        [InputParameter("Show MBO icebergs (real)", 28)]
        public bool ShowMboIce = true;        // real trade-anchored absorption from the backend detector (NQ/ES/RTY)
        [InputParameter("Show MBO walls (resting)", 29)]
        public bool ShowMboWalls = true;      // biggest resting orders from the real MBO book (support below / resistance above)
        [InputParameter("Bubbles only at walls (hits)", 30)]
        public bool BubblesOnlyAtWalls = true; // a print only draws a bubble if it traded AT a resting wall (kills per-trade noise)
        [InputParameter("Show trapped traders", 31)]
        public bool ShowTraps = true;          // levels where aggressive traders are offside (red=trapped longs/resist, green=trapped shorts/support)
        [InputParameter("Show wall fill/cancel histogram", 32)]
        public bool ShowFlow = true;           // bottom strip: green ▲ = wall fill / red ▼ = wall cancel, per minute
        [InputParameter("Show exhaustion model + fires", 9)]
        public bool ShowExhaustion = true;
        [InputParameter("Show regime banner", 10)]
        public bool ShowRegime = true;
        [InputParameter("Show expected-move band", 12)]
        public bool ShowRangeBand = true;
        [InputParameter("Band MA length", 13, 1, 500, 1, 0)]
        public int BandMaLength = 20;
        [InputParameter("Band width %", 14, 5, 400, 5, 0)]
        public double BandWidthPct = 100;
        [InputParameter("Auto-scale thresholds to asset", 15)]
        public bool AutoScale = true;
        [InputParameter("Max walls shown (biggest)", 16, 1, 50, 1, 0)]
        public int MaxWalls = 6;           // show at most this many walls — the biggest, genuinely-outsized levels
        [InputParameter("Big print = top % of trades (auto)", 23, 50, 99.9, 0.5, 1)]
        public double PrintPctile = 98;    // a big print = bigger than this % of recent trades
        [InputParameter("Iceberg min = N x typical book", 17, 1.0, 50.0, 0.5, 1)]
        public double IceMinMult = 6.0;
        [InputParameter("Off-NQ band (volatility)", 18)]
        public bool ShowBandOffNq = true;
        [InputParameter("Off-NQ band sigma", 19, 0.5, 6.0, 0.5, 1)]
        public double BandSigma = 2.0;
        [InputParameter("Hold spent levels (footprints)", 20)]
        public bool HoldLevels = true;
        [InputParameter("Invalidate after price thru (ticks)", 21, 1, 200, 1, 0)]
        public double InvalidateTicks = 6;
        [InputParameter("Footprint max age (min)", 22, 1, 480, 1, 0)]
        public int LevelMaxAgeMin = 30;

        private static readonly HttpClient Http = new HttpClient { Timeout = TimeSpan.FromSeconds(6) };
        private static readonly HttpClient HttpStream = new HttpClient { Timeout = TimeSpan.FromSeconds(35) };   // long-poll the live MBO stream (server holds ~25s)
        private Thread _streamThread;
        private CancellationTokenSource _streamCts;   // per-thread cancel: OnClear cancels THIS thread's token (incl. its in-flight GET); OnInit makes a NEW one so a prior thread can't be un-stopped
        private readonly Font _font = new Font("Segoe UI", 8f);
        private readonly Font _fontB = new Font("Segoe UI", 8f, FontStyle.Bold);
        private readonly Font _fontReg = new Font("Segoe UI", 9f, FontStyle.Bold);

        private Timer _domTimer;
        private Timer _exhTimer;
        private int _domBusy;
        private int _exhBusy;
        private int _modelTick;
        private int _exhCount;

        private readonly object _lock = new object();
        private readonly Dictionary<double, Lvl> _levels = new Dictionary<double, Lvl>();
        private readonly List<Print> _prints = new List<Print>();

        private volatile RenderState _state = new RenderState();
        private volatile ExhState _exh = new ExhState();
        private volatile Fire[] _fires = new Fire[0];
        private volatile GammaState _gamma = new GammaState();
        private volatile IceFlow[] _iceflow = new IceFlow[0];
        private volatile MboWall[] _mbowalls = new MboWall[0];
        private volatile TrapLevel[] _traps = new TrapLevel[0];
        private volatile FlowBar[] _flow = new FlowBar[0];
        private volatile FillMark[] _fillmarks = new FillMark[0];
        private int _gammaTick;

        private double _bookScale;                                   // EWMA of the median resting size -> per-asset book scale
        private double _effWall = 25, _effBigPrint = 10, _effIceMin = 30;  // live-calibrated thresholds
        private readonly List<double> _recentTradeSizes = new List<double>();
        private double _lastTradePrice;                              // for footprint invalidation (price traded through?)
        private readonly Dictionary<double, Mark> _marks = new Dictionary<double, Mark>();  // lingering absorption/iceberg footprints

        public InSyncOrderflow() : base()
        {
            Name = "InSync Orderflow";
            SeparateWindow = false;
        }

        protected override void OnInit()
        {
            if (Symbol != null)
            {
                Symbol.NewLevel2 += OnNewLevel2;   // REQUIRED: triggers the vendor order-book subscription
                Symbol.NewLast += OnNewLast;       // executed trades (tape)
            }
            _domTimer = new Timer(_ => DomTick(), null, 400, 400);
            _exhTimer = new Timer(_ => ExhTick(), null, 0, 250);   // 250ms tick: file-poll FALLBACK for MBO + the ~3s model fetch (every 12th)
            _streamCts = new CancellationTokenSource();
            var stok = _streamCts.Token;
            _streamThread = new Thread(() => StreamLoop(stok)) { IsBackground = true, Name = "InSyncOrderflowStream" };
            _streamThread.Start();   // PRIMARY MBO path: real-time long-poll stream
        }

        protected override void OnClear()
        {
            _domTimer?.Dispose(); _domTimer = null;
            _exhTimer?.Dispose(); _exhTimer = null;
            try { _streamCts?.Cancel(); } catch { }   // cancels this thread's loop AND its in-flight long-poll GET -> exits promptly, no zombie, no UI block
            _streamCts = null; _streamThread = null;
            if (Symbol != null)
            {
                Symbol.NewLevel2 -= OnNewLevel2;
                Symbol.NewLast -= OnNewLast;
            }
            lock (_lock) { _levels.Clear(); _prints.Clear(); }
        }

        private static DateTime NowUtc()
        {
            try { return Core.Instance.TimeUtils.DateTimeUtcNow; } catch { return DateTime.UtcNow; }
        }

        // the regime/exhaustion model is NQ-trained only -> gate the model overlay to NQ (and the NQ micro) charts
        private bool IsNqChart()
        {
            try { string n = (Symbol?.Name ?? "").Trim().TrimStart('/').ToUpperInvariant(); return n.StartsWith("NQ") || n.StartsWith("MNQ"); }
            catch { return false; }
        }

        // chart symbol -> options-levels futures key (NQ/ES/RTY mapped; micros share the parent index)
        private string GammaKey()
        {
            try {
                string n = (Symbol?.Name ?? "").Trim().TrimStart('/').ToUpperInvariant();
                if (n.StartsWith("MNQ") || n.StartsWith("NQ")) return "NQ.c.0";
                if (n.StartsWith("MES") || n.StartsWith("ES")) return "ES.c.0";
                if (n.StartsWith("M2K") || n.StartsWith("RTY")) return "RTY.c.0";
            } catch { }
            return null;
        }

        // background thread
        private void OnNewLevel2(Symbol s, Level2Quote q, DOMQuote dom) { /* feed kept alive; snapshot polled in DomTick */ }

        // background thread
        private void OnNewLast(Symbol s, Last last)
        {
            double px = last.Price, sz = last.Size;
            if (px <= 0 || sz <= 0) return;
            bool buy = last.AggressorFlag == AggressorFlag.Buy;
            bool sell = last.AggressorFlag == AggressorFlag.Sell;
            DateTime now = NowUtc();
            lock (_lock)
            {
                _lastTradePrice = px;
                if (!_levels.TryGetValue(px, out var lv)) { lv = new Lvl(); _levels[px] = lv; }
                lv.Traded += sz;
                lv.TradedRecent += sz;
                lv.LastTrade = now;
                _recentTradeSizes.Add(sz);
                if (_recentTradeSizes.Count > 1000) _recentTradeSizes.RemoveAt(0);
                double printFloor = BubbleMode ? Math.Max(2, _effBigPrint * 0.6) : _effBigPrint;  // bubbles: a bit more flow than triangles, not every tick
                int printCap = BubbleMode ? Math.Max(10, MaxBubbles) : 80;
                if (ShowPrints && sz >= printFloor)
                {
                    _prints.Add(new Print { Time = now, Price = px, Size = sz, Buy = buy, Sell = sell });
                    if (_prints.Count > printCap)   // keep the biggest so a fast tape (ES) can't flood the chart
                    {
                        int mi = 0; for (int i = 1; i < _prints.Count; i++) if (_prints[i].Size < _prints[mi].Size) mi = i;
                        _prints.RemoveAt(mi);
                    }
                }
            }
        }

        private void DomTick()
        {
            if (Interlocked.Exchange(ref _domBusy, 1) == 1) return;
            try
            {
                var rs = new RenderState();
                Symbol sym = Symbol;
                if (sym?.DepthOfMarket != null)
                {
                    var dom = sym.DepthOfMarket.GetDepthOfMarketAggregatedCollections(new GetLevel2ItemsParameters
                    {
                        AggregateMethod = AggregateMethod.ByPriceLVL,
                        LevelsCount = DomLevels,
                        CalculateCumulative = true
                    });
                    if (dom?.Bids != null && dom.Asks != null)
                    {
                        double bidSum = dom.Bids.Take(ImbalanceLevels).Sum(x => x.Size);
                        double askSum = dom.Asks.Take(ImbalanceLevels).Sum(x => x.Size);
                        rs.BidSum = bidSum; rs.AskSum = askSum;
                        rs.HasImb = (bidSum + askSum) > 0;
                        rs.Imbalance = askSum > 0 ? bidSum / askSum : 0;

                        DateTime now = NowUtc();
                        lock (_lock)
                        {
                            foreach (var lv in _levels.Values) lv.CurSize = 0;
                            foreach (var it in dom.Bids) Touch(it.Price, it.Size, it.NumberOrders, true);
                            foreach (var it in dom.Asks) Touch(it.Price, it.Size, it.NumberOrders, false);

                            var remove = new List<double>();
                            foreach (var kv in _levels)
                            {
                                var lv = kv.Value;
                                lv.TradedRecent *= 0.95;   // rolling decay (~5s half-life) so "recent" volume fades — chop no longer floods icebergs
                                if ((now - lv.LastTrade).TotalSeconds > 45) lv.TradedRecent = 0;
                                if (lv.CurSize <= 0 && (now - lv.LastTrade).TotalSeconds > 90) remove.Add(kv.Key);
                            }
                            foreach (var k in remove) _levels.Remove(k);

                            // auto-calibrate the size thresholds to THIS asset from the live book + tape
                            if (AutoScale)
                            {
                                var sizes = new List<double>();
                                foreach (var lvv in _levels.Values) if (lvv.CurSize > 0) sizes.Add(lvv.CurSize);
                                if (sizes.Count > 0)
                                {
                                    sizes.Sort();
                                    double medNow = sizes[sizes.Count / 2];
                                    _bookScale = _bookScale <= 0 ? medNow : 0.92 * _bookScale + 0.08 * medNow;
                                    // wall threshold = the (MaxWalls)-th biggest level, but never below 2x the typical level ->
                                    // you get AT MOST MaxWalls walls, and only genuinely outsized ones (no flooding on deep books)
                                    int nth = Math.Max(0, sizes.Count - Math.Max(1, MaxWalls));
                                    _effWall = Math.Max(2, Math.Max(sizes[nth], 2.0 * _bookScale));
                                    _effIceMin = Math.Max(2, IceMinMult * _bookScale);
                                }
                                if (_recentTradeSizes.Count >= 20)
                                {
                                    var ts = new List<double>(_recentTradeSizes); ts.Sort();
                                    int pi = Math.Min(ts.Count - 1, (int)(ts.Count * (PrintPctile / 100.0)));
                                    _effBigPrint = Math.Max(2, ts[pi]);   // big print = bigger than PrintPctile% of recent trades
                                }
                            }
                            else { _effWall = WallSize; _effIceMin = IcebergMinVol; _effBigPrint = BigPrintSize; }

                            foreach (var kv in _levels)
                            {
                                var lv = kv.Value;
                                bool wall = lv.CurSize >= _effWall;
                                // iceberg = a level still showing size that's REFILLING: RECENT (decaying) volume traded through
                                // it is many times the most it ever displayed, over a meaningful minimum (so chop doesn't flood it).
                                bool ice = lv.CurSize > 0 && lv.MaxSize > 0
                                           && lv.TradedRecent >= lv.MaxSize * IcebergMult
                                           && lv.TradedRecent >= _effIceMin;
                                bool abs = wall && lv.TradedRecent >= _effWall;
                                if (wall || ice)
                                    rs.Walls.Add(new Wall { Price = kv.Key, Size = lv.CurSize, Eaten = lv.TradedRecent, IsBid = lv.IsBid, Iceberg = ice, Absorption = abs });
                            }

                            // FOOTPRINTS: keep significant absorption/iceberg levels lingering until price invalidates them
                            if (HoldLevels)
                            {
                                double tickSz = (Symbol != null && Symbol.TickSize > 0) ? Symbol.TickSize : 0.25;
                                double lastPx = _lastTradePrice;
                                foreach (var m in _marks.Values) m.LiveNow = false;
                                foreach (var w in rs.Walls)
                                {
                                    if (!(w.Iceberg || w.Absorption)) continue;
                                    if (!_marks.TryGetValue(w.Price, out var m)) { m = new Mark { Price = w.Price, IsBid = w.IsBid }; _marks[w.Price] = m; }
                                    m.LiveNow = true; m.LastActive = now; m.IsBid = w.IsBid;
                                    m.Iceberg |= w.Iceberg; m.Absorption |= w.Absorption;
                                    if (w.Size > m.PeakSize) m.PeakSize = w.Size;
                                    if (w.Eaten > m.PeakEaten) m.PeakEaten = w.Eaten;
                                }
                                double margin = InvalidateTicks * tickSz;
                                var dropM = new List<double>();
                                foreach (var kv in _marks)
                                {
                                    var m = kv.Value;
                                    bool through = lastPx > 0 && (m.IsBid ? lastPx < m.Price - margin : lastPx > m.Price + margin);
                                    if (through || (now - m.LastActive).TotalMinutes > LevelMaxAgeMin) dropM.Add(kv.Key);
                                }
                                foreach (var k in dropM) _marks.Remove(k);
                                while (_marks.Count > 30)   // bound: drop the oldest
                                {
                                    double ok = 0; DateTime ot = DateTime.MaxValue;
                                    foreach (var kv in _marks) if (kv.Value.LastActive < ot) { ot = kv.Value.LastActive; ok = kv.Key; }
                                    _marks.Remove(ok);
                                }
                                foreach (var m in _marks.Values)
                                    if (!m.LiveNow)
                                        rs.GhostLevels.Add(new Ghost { Price = m.Price, IsBid = m.IsBid, Iceberg = m.Iceberg, Absorption = m.Absorption, PeakSize = m.PeakSize, PeakEaten = m.PeakEaten, AgeSec = (int)(now - m.LastActive).TotalSeconds });
                            }
                            else if (_marks.Count > 0) _marks.Clear();
                        }
                    }
                }
                lock (_lock)
                {
                    DateTime now = NowUtc();
                    _prints.RemoveAll(p => (now - p.Time).TotalMinutes > 5);
                    rs.Prints = _prints.ToList();
                }
                _state = rs;
            }
            catch { }
            finally { Interlocked.Exchange(ref _domBusy, 0); }
        }

        private void Touch(double price, double size, int orders, bool isBid)
        {
            if (!_levels.TryGetValue(price, out var lv)) { lv = new Lvl(); _levels[price] = lv; }
            lv.CurSize = size;
            lv.Orders = orders;
            lv.IsBid = isBid;
            if (size > lv.MaxSize) lv.MaxSize = size;
        }

        // parse one detector payload (from the file poll OR the live stream — same shape) into the render arrays
        private void ParseMboPayload(JsonElement r)
        {
            var ilist = new List<IceFlow>();
            if (r.TryGetProperty("events", out var ievs) && ievs.ValueKind == JsonValueKind.Array)
                foreach (var ev in ievs.EnumerateArray())
                {
                    double? px = Dbl(ev, "price"); double? tms = Dbl(ev, "ts_ms");
                    if (!px.HasValue || !tms.HasValue) continue;
                    var sd = (Str(ev, "side") ?? "").ToUpperInvariant();
                    var kd = (Str(ev, "kind") ?? "").ToLowerInvariant();
                    ilist.Add(new IceFlow { Time = DateTimeOffset.FromUnixTimeMilliseconds((long)tms.Value).UtcDateTime, Price = px.Value, Absorbed = Dbl(ev, "absorbed") ?? 0, IsBid = sd.StartsWith("B"), Iceberg = kd == "iceberg", Sweep = kd == "sweep", Pull = kd == "pull" });
                }
            _iceflow = ilist.OrderByDescending(z => z.Absorbed).Take(60).ToArray();
            var wlist = new List<MboWall>();
            if (r.TryGetProperty("walls", out var wevs) && wevs.ValueKind == JsonValueKind.Array)
                foreach (var w in wevs.EnumerateArray())
                {
                    double? wp = Dbl(w, "price"); double wsz = Dbl(w, "size") ?? 0;
                    if (!wp.HasValue || wsz <= 0) continue;
                    wlist.Add(new MboWall { Price = wp.Value, Size = wsz, Orders = (int)(Dbl(w, "orders") ?? 0), Filled = (int)(Dbl(w, "filled") ?? 0), Cancelled = (int)(Dbl(w, "cancelled") ?? 0), Side = Str(w, "side") });
                }
            _mbowalls = wlist.ToArray();
            var tlist = new List<TrapLevel>();
            if (r.TryGetProperty("traps", out var tevs) && tevs.ValueKind == JsonValueKind.Array)
                foreach (var t in tevs.EnumerateArray())
                {
                    double? tpp = Dbl(t, "price"); double tvv = Dbl(t, "vol") ?? 0;
                    if (!tpp.HasValue || tvv <= 0) continue;
                    double? ttms = Dbl(t, "ts_ms");
                    tlist.Add(new TrapLevel { Price = tpp.Value, Vol = (int)tvv, IsLong = (Str(t, "kind") ?? "") == "trap_long", Time = ttms.HasValue ? DateTimeOffset.FromUnixTimeMilliseconds((long)ttms.Value).UtcDateTime : default });
                }
            _traps = tlist.ToArray();
            var flist = new List<FlowBar>();
            if (r.TryGetProperty("flow", out var flarr) && flarr.ValueKind == JsonValueKind.Array)
                foreach (var fb in flarr.EnumerateArray())
                {
                    double? fts = Dbl(fb, "ts_ms");
                    if (!fts.HasValue) continue;
                    double bff = Dbl(fb, "bull_fill") ?? -1, sff = Dbl(fb, "sell_fill") ?? -1, tff = Dbl(fb, "fill") ?? 0;
                    if (bff < 0 && sff < 0) { bff = tff; sff = 0; }   // old backend w/o side split -> all into bull bucket
                    else { if (bff < 0) bff = 0; if (sff < 0) sff = 0; }
                    flist.Add(new FlowBar { Time = DateTimeOffset.FromUnixTimeMilliseconds((long)fts.Value).UtcDateTime, BullFill = bff, SellFill = sff, Fill = bff + sff, Cancel = Dbl(fb, "cancel") ?? 0 });
                }
            _flow = flist.ToArray();
            var fmlist = new List<FillMark>();
            if (r.TryGetProperty("fillmarks", out var fmarr) && fmarr.ValueKind == JsonValueKind.Array)
                foreach (var fmj in fmarr.EnumerateArray())
                {
                    double? mts = Dbl(fmj, "ts_ms"); double? mpx = Dbl(fmj, "price");
                    if (!mts.HasValue || !mpx.HasValue) continue;
                    fmlist.Add(new FillMark { Time = DateTimeOffset.FromUnixTimeMilliseconds((long)mts.Value).UtcDateTime, Price = mpx.Value, Side = Str(fmj, "side"), Filled = (int)(Dbl(fmj, "filled") ?? 0) });
                }
            _fillmarks = fmlist.ToArray();
        }

        // LIVE STREAM: long-poll /iceberg-flow/wait — returns the instant the detector publishes a change,
        // so walls/fills update in ~real time (no fixed poll interval). Self-healing: any error just re-polls.
        private void StreamLoop(CancellationToken tok)
        {
            long seq = 0; string lastRoot = null;
            while (!tok.IsCancellationRequested)
            {
                try
                {
                    if (!(ShowMboIce || ShowMboWalls || ShowTraps || BubblesOnlyAtWalls)) { Thread.Sleep(500); continue; }
                    string gkey = GammaKey();
                    if (gkey == null) { Thread.Sleep(500); continue; }
                    string root = gkey.Split('.')[0];
                    if (root != lastRoot) { seq = 0; lastRoot = root; }   // chart symbol changed -> start fresh
                    string url = BackendUrl.TrimEnd('/') + "/api/monitor/iceberg-flow/wait?symbol=" + Uri.EscapeDataString(root) + "&since=" + seq + "&timeout=25";
                    string json = HttpStream.GetStringAsync(url, tok).GetAwaiter().GetResult();   // tok cancels the in-flight GET when OnClear fires
                    if (tok.IsCancellationRequested) break;
                    using var doc = JsonDocument.Parse(json);
                    var rt = doc.RootElement;
                    long ns = (long)(Dbl(rt, "seq") ?? seq);
                    if (ns == seq) continue;   // long-poll timed out with no change -> immediately re-poll
                    seq = ns;
                    ParseMboPayload(rt);
                }
                catch { if (!tok.IsCancellationRequested) Thread.Sleep(800); }   // detector/backend restart or hiccup -> back off, then reconnect
            }
        }

        private void ExhTick()
        {
            if (Interlocked.Exchange(ref _exhBusy, 1) == 1) return;
            try
            {
                // GAMMA profile (per-asset: NQ/ES/RTY) — runs BEFORE the NQ gate, slow cadence (~24s)
                string gkey = GammaKey();
                if (gkey == null) _gamma = new GammaState();
                else if (_gammaTick++ % 96 == 0)   // ~24s at the 250ms tick
                {
                    try
                    {
                        string gjson = Http.GetStringAsync(BackendUrl.TrimEnd('/') + "/api/monitor/options-levels").GetAwaiter().GetResult();
                        using var gdoc = JsonDocument.Parse(gjson);
                        var g = new GammaState();
                        if (gdoc.RootElement.TryGetProperty("futures", out var futs) && futs.TryGetProperty(gkey, out var fo))
                        {
                            g.PanelPx = Dbl(fo, "future_px") ?? 0;
                            if (fo.TryGetProperty("levels", out var lvls) && lvls.ValueKind == JsonValueKind.Array)
                                foreach (var lvl in lvls.EnumerateArray())
                                {
                                    double px = Dbl(lvl, "price") ?? 0; if (px <= 0) continue;
                                    switch (Str(lvl, "kind"))
                                    {
                                        case "zero_gamma": g.Flip = px; break;
                                        case "call_wall": g.CallWall = px; break;
                                        case "gex_wall_neg": g.GexNeg = px; break;
                                        case "max_pain": g.MaxPain = px; break;
                                    }
                                }
                            g.Ok = g.Flip > 0;
                        }
                        _gamma = g;
                    }
                    catch { /* keep previous gamma */ }
                }

                // REAL MBO icebergs/absorption (per-asset: NQ/ES/RTY) — backend detector off the Rithmic order-by-order feed
                if ((ShowMboIce || ShowMboWalls || ShowTraps || BubblesOnlyAtWalls) && gkey != null)   // fetch walls/traps/icebergs if ANY consumer needs them (not just ShowMboIce)
                {
                    try
                    {
                        string root = gkey.Split('.')[0];
                        string ijson = Http.GetStringAsync(BackendUrl.TrimEnd('/') + "/api/monitor/iceberg-flow?symbol=" + Uri.EscapeDataString(root)).GetAwaiter().GetResult();
                        using var idoc = JsonDocument.Parse(ijson);
                        ParseMboPayload(idoc.RootElement);
                    }
                    catch { /* keep previous icebergs */ }
                }
                else if (gkey == null) { _iceflow = new IceFlow[0]; _mbowalls = new MboWall[0]; _traps = new TrapLevel[0]; _flow = new FlowBar[0]; _fillmarks = new FillMark[0]; }   // unsupported symbol -> clear ALL MBO arrays (no stale data on CL/GC etc.)

                if (_modelTick++ % 12 != 0) return;   // MBO above refreshes every 250ms tick; the heavier model/state fetch only needs ~3s
                if ((!ShowExhaustion && !ShowRegime) || !IsNqChart()) { _exh = new ExhState(); _fires = new Fire[0]; return; }

                // 1) current state: reversal + regime
                string url = BackendUrl.TrimEnd('/') + "/api/monitor/market-state?symbol=" + Uri.EscapeDataString(MarketStateSymbol);
                string json = Http.GetStringAsync(url).GetAwaiter().GetResult();
                using (var doc = JsonDocument.Parse(json))
                {
                    var e = new ExhState();
                    if (doc.RootElement.TryGetProperty("tiles", out var tiles))
                    {
                        if (tiles.TryGetProperty("reversal", out var rev))
                        {
                            e.Status = Str(rev, "status");
                            e.Fired = rev.TryGetProperty("fired", out var f) && f.ValueKind == JsonValueKind.True;
                            e.Prob = Dbl(rev, "reversal_prob") ?? 0;
                            e.Exhaust = Dbl(rev, "exhaust") ?? 0;
                            e.Strength = Str(rev, "strength");
                            e.LegDir = (int)(Dbl(rev, "leg_dir") ?? 0);
                            e.EventPrice = Dbl(rev, "event_price") ?? 0;
                            e.EventTsMs = Lng(rev, "event_ts_ms") ?? 0;
                            e.MinutesAgo = (int)(Dbl(rev, "minutes_ago") ?? -1);
                        }
                        if (tiles.TryGetProperty("move_size", out var mv))
                        {
                            e.RegimeStatus = Str(mv, "status");
                            e.Regime = Str(mv, "regime");
                            e.RegimeRangeT = Dbl(mv, "regime_range_t") ?? 0;
                            e.RegimeAnchor = Dbl(mv, "anchor") ?? 0;
                        }
                    }
                    _exh = e;
                }

                // 2) history: every fire today (lower cadence — fires are rare; ~every 15s)
                if (ShowExhaustion && (_exhCount++ % 5) == 0)
                {
                    string hurl = BackendUrl.TrimEnd('/') + "/api/monitor/reversal-history?symbol=" + Uri.EscapeDataString(MarketStateSymbol);
                    string hjson = Http.GetStringAsync(hurl).GetAwaiter().GetResult();
                    using var hdoc = JsonDocument.Parse(hjson);
                    var list = new List<Fire>();
                    if (hdoc.RootElement.TryGetProperty("events", out var evs) && evs.ValueKind == JsonValueKind.Array)
                    {
                        foreach (var ev in evs.EnumerateArray())
                        {
                            double? px = Dbl(ev, "event_price");
                            long? tms = Lng(ev, "ts_ms");
                            if (!px.HasValue || !tms.HasValue) continue;
                            list.Add(new Fire
                            {
                                Time = DateTimeOffset.FromUnixTimeMilliseconds(tms.Value).UtcDateTime,
                                Price = px.Value,
                                Prob = Dbl(ev, "reversal_prob") ?? 0,
                                Exhaust = Dbl(ev, "exhaust") ?? 0,
                                LegDir = (int)(Dbl(ev, "leg_dir") ?? 0),
                                Fired = ev.TryGetProperty("fired", out var ff) && ff.ValueKind == JsonValueKind.True,
                                Strength = Str(ev, "strength"),
                            });
                        }
                    }
                    _fires = list.ToArray();
                }
            }
            catch { /* keep previous snapshots */ }
            finally { Interlocked.Exchange(ref _exhBusy, 0); }
        }

        private static string Str(JsonElement e, string p) => e.TryGetProperty(p, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
        private static double? Dbl(JsonElement e, string p) => e.TryGetProperty(p, out var v) && v.ValueKind == JsonValueKind.Number && v.TryGetDouble(out var d) ? d : (double?)null;
        private static long? Lng(JsonElement e, string p) => e.TryGetProperty(p, out var v) && v.ValueKind == JsonValueKind.Number && v.TryGetInt64(out var d) ? d : (long?)null;

        // UTC -> the chart's OWN displayed timezone (so the printed time matches the axis), formatted "7:14a" / "12:03p"
        private string Clock(DateTime utc)
        {
            var u = DateTime.SpecifyKind(utc, DateTimeKind.Utc);
            DateTime t;
            try
            {
                var tz = CurrentChart?.CurrentTimeZone;   // TimeZone is a struct -> ?. yields TimeZone?
                if (tz.HasValue && !tz.Value.IsEmpty && tz.Value.TimeZoneInfo != null)
                    t = TimeZoneInfo.ConvertTimeFromUtc(u, tz.Value.TimeZoneInfo);
                else
                    t = u.ToLocalTime();
            }
            catch { t = u.ToLocalTime(); }
            return t.ToString("h:mmt").ToLowerInvariant();
        }

        // wall book side -> -1 bid/bull-limit (teal), +1 ask/sell-limit (orange), 0 unknown (neutral gray).
        // uses the real MBO side; only falls back to price-relative when side is genuinely missing.
        private static int WallSide(string side, double price, double px0)
        {
            if (side == "B") return -1;
            if (side == "A") return 1;
            if (px0 > 0) return price < px0 ? -1 : 1;
            return 0;
        }

        public override void OnPaintChart(PaintChartEventArgs args)
        {
            var rs = _state; var exh = _exh; var fires = _fires; var ice = _iceflow; var mw = _mbowalls; var tps = _traps; var fl = _flow; var fm2 = _fillmarks;
            bool isNq = IsNqChart();   // model overlay (fires / rev-watch / model band) is valid on NQ only
            var windows = CurrentChart?.Windows;
            if (windows == null || args.WindowIndex < 0 || args.WindowIndex >= windows.Count()) return;
            var conv = windows[args.WindowIndex].CoordinatesConverter;
            if (conv == null) return;
            Graphics gr = args.Graphics;
            Rectangle rect = args.Rectangle;
            int Y(double px) { try { return (int)conv.GetChartY(px); } catch { return int.MinValue; } }
            int X(DateTime t) { try { return (int)conv.GetChartX(t); } catch { return int.MinValue; } }

            // PULLED-PER-MINUTE STRIP — bottom: red bars = total wall size CANCELLED (pulled) each minute. Fills now print on the candles as +N/-N.
            if (ShowFlow && fl != null && fl.Length > 0)
            {
                int sH = Math.Min(70, Math.Max(40, rect.Height / 7));
                int sTop = rect.Bottom - sH;
                int baseY = rect.Bottom - 3;
                int hmax = sH - 16;
                double mxc = 1;
                foreach (var b in fl) if (b.Cancel > mxc) mxc = b.Cancel;
                int bw = 4;
                { int x0 = X(fl[0].Time); int x1 = X(fl[0].Time.AddMinutes(1)); if (x0 != int.MinValue && x1 != int.MinValue) bw = Math.Max(2, Math.Min(16, (int)(Math.Abs(x1 - x0) * 0.6))); }
                using (var bgs = new SolidBrush(Color.FromArgb(150, 8, 12, 20)))
                    gr.FillRectangle(bgs, rect.Left, sTop, rect.Width, sH);
                using (var rf = new SolidBrush(ColorTranslator.FromHtml("#ef4444")))
                    foreach (var b in fl)
                    {
                        int x = X(b.Time);
                        if (x == int.MinValue || x < rect.Left - bw || x > rect.Right + bw) continue;
                        int ch = (int)(b.Cancel / mxc * hmax);
                        if (ch > 0) gr.FillRectangle(rf, x - bw / 2, baseY - ch, bw, ch);
                    }
                using (var lb = new SolidBrush(Color.FromArgb(185, 200, 210, 220)))
                    gr.DrawString("pulled / min — wall size cancelled (red)", _font, lb, rect.Left + 4, sTop + 2);
            }

            Color magenta = ColorTranslator.FromHtml("#e879f9");

            // walls / icebergs / absorption
            if (false && ShowWalls && rs.Walls != null)   // DECLUTTER: old MBP heuristic walls/abs/ice ticks OFF (flip false->true to restore)
            {
                foreach (var w in rs.Walls)
                {
                    int y = Y(w.Price);
                    if (y == int.MinValue || y < rect.Top - 2 || y > rect.Bottom + 2) continue;
                    Color c = w.IsBid ? ColorTranslator.FromHtml("#2dd4bf") : ColorTranslator.FromHtml("#fb923c");
                    bool loud = w.Iceberg || w.Absorption;   // a resting block getting HIT but holding = the moment that matters
                    if (loud)
                    {
                        // short bright TICK at the price (not full-width) + glow + bold tab: size HELD vs recent volume that HIT it
                        using (var glow = new Pen(Color.FromArgb(80, c), 6f))
                            gr.DrawLine(glow, rect.Right - 80, y, rect.Right, y);
                        using (var pen = new Pen(Color.FromArgb(255, c), 2.5f))
                            gr.DrawLine(pen, rect.Right - 80, y, rect.Right, y);
                        string txt = (w.Iceberg ? "ICEBERG" : "ABSORBING") + "  " + w.Size.ToString("0")
                                     + " held · " + w.Eaten.ToString("0") + " hit  @ " + w.Price.ToString("0.##");
                        var tsz = gr.MeasureString(txt, _fontB);
                        float lx = rect.Right - tsz.Width - 14;
                        using (var bg = new SolidBrush(Color.FromArgb(210, 0, 0, 0)))
                            gr.FillRectangle(bg, lx - 5, y - 16, tsz.Width + 10, 16);
                        using (var barB = new SolidBrush(c))
                            gr.FillRectangle(barB, lx - 5, y - 16, 3, 16);
                        using (var br = new SolidBrush(c))
                            gr.DrawString(txt, _fontB, br, lx, y - 15);
                    }
                    else if (ShowPlainWalls)
                    {
                        using (var pen = new Pen(Color.FromArgb(150, c), 1.5f))
                            gr.DrawLine(pen, rect.Right - 215, y, rect.Right, y);
                        using (var br = new SolidBrush(Color.FromArgb(205, c)))
                            gr.DrawString("wall " + w.Size.ToString("0") + " @ " + w.Price.ToString("0.##"), _font, br, rect.Right - 213, y - 13);
                    }
                }
            }

            // FOOTPRINTS — spent absorption/iceberg levels that price hasn't invalidated yet ("where size was positioned")
            if (false && ShowWalls && rs.GhostLevels != null)   // DECLUTTER: old footprints OFF (flip false->true to restore)
            {
                foreach (var g in rs.GhostLevels)
                {
                    int y = Y(g.Price);
                    if (y == int.MinValue || y < rect.Top - 2 || y > rect.Bottom + 2) continue;
                    Color c = g.IsBid ? ColorTranslator.FromHtml("#2dd4bf") : ColorTranslator.FromHtml("#fb923c");
                    using (var pen = new Pen(Color.FromArgb(120, c), 1.3f) { DashStyle = DashStyle.Dash })
                        gr.DrawLine(pen, rect.Right - 60, y, rect.Right, y);
                    string tag = (g.Iceberg ? "ICE" : "ABS") + " " + g.PeakSize.ToString("0")
                                 + (g.AgeSec >= 60 ? "  " + (g.AgeSec / 60) + "m" : "");
                    using (var br = new SolidBrush(Color.FromArgb(210, c)))
                        gr.DrawString(tag, _fontB, br, rect.Right - 318, y - 13);
                }
            }

            // REAL MBO resting WALLS — line + "wall <size> ×<orders>" label, colored by BOOK SIDE (teal=bid/bull-limit, orange=ask/sell-limit).
            if (ShowMboWalls && mw != null && mw.Length > 0)
            {
                double px0 = 0; try { if (Count > 0) px0 = Close(0); } catch { }
                foreach (var w in mw)
                {
                    int y = Y(w.Price);
                    if (y == int.MinValue || y < rect.Top || y > rect.Bottom) continue;
                    int sd = WallSide(w.Side, w.Price, px0);   // -1 bid/bull, +1 ask/sell, 0 unknown (real MBO book side)
                    Color c = sd < 0 ? ColorTranslator.FromHtml("#2dd4bf") : sd > 0 ? ColorTranslator.FromHtml("#fb923c") : ColorTranslator.FromHtml("#9aa4af");
                    float th = (float)Math.Max(1.5, Math.Min(6, w.Size / 40.0));   // thicker line = bigger wall
                    int x0 = rect.Right - 210;
                    using (var pen = new Pen(Color.FromArgb(125, c), th))
                        gr.DrawLine(pen, x0, y, rect.Right, y);
                    string wl = "wall " + w.Size.ToString("0") + (w.Orders > 0 ? " ×" + w.Orders : "");
                    using (var bg = new SolidBrush(Color.FromArgb(170, 0, 0, 0)))
                        gr.FillRectangle(bg, x0 - 2, y - 13, gr.MeasureString(wl, _font).Width + 4, 13);
                    using (var br = new SolidBrush(c))
                        gr.DrawString(wl, _font, br, x0, y - 13);
                }
            }

            // FILL MARKERS — on the candle that filled a wall: +N teal (bid/bull-limit hit) / -N orange (ask/sell-limit hit), drawn at the wall price
            if (ShowMboWalls && fm2 != null && fm2.Length > 0)
            {
                double px0 = 0; try { if (Count > 0) px0 = Close(0); } catch { }
                foreach (var f in fm2)
                {
                    int x = X(f.Time), y = Y(f.Price);
                    if (x == int.MinValue || y == int.MinValue || x < rect.Left || x > rect.Right || y < rect.Top || y > rect.Bottom) continue;
                    int s2 = WallSide(f.Side, f.Price, px0);
                    string lbl = (s2 < 0 ? "+" : s2 > 0 ? "-" : "") + f.Filled;
                    Color c = s2 < 0 ? ColorTranslator.FromHtml("#2dd4bf") : s2 > 0 ? ColorTranslator.FromHtml("#fb923c") : ColorTranslator.FromHtml("#9aa4af");
                    float w2 = gr.MeasureString(lbl, _font).Width;
                    using (var bg = new SolidBrush(Color.FromArgb(165, 0, 0, 0)))
                        gr.FillRectangle(bg, x - w2 / 2 - 1, y - 7, w2 + 2, 13);
                    using (var br = new SolidBrush(c))
                        gr.DrawString(lbl, _font, br, x - w2 / 2, y - 7);
                }
            }

            // TRAPPED traders — aggressive size now offside (red = trapped longs / overhead supply, green = trapped shorts / demand below)
            if (false && ShowTraps && tps != null && tps.Length > 0)   // DECLUTTER: trapped-trader lines OFF (flip false->true to restore)
            {
                DateTime nowT = default; try { if (Count > 0) nowT = Time(0); } catch { }
                foreach (var tp in tps)
                {
                    int y = Y(tp.Price);
                    if (y == int.MinValue || y < rect.Top || y > rect.Bottom) continue;
                    int x1 = (tp.Time == default) ? rect.Left : X(tp.Time);   // anchored to the candle where they got trapped
                    int x2 = (nowT == default) ? rect.Right : X(nowT);
                    if (x1 == int.MinValue) x1 = rect.Left;
                    if (x2 == int.MinValue) x2 = rect.Right;
                    x1 = Math.Max(rect.Left, Math.Min(x1, rect.Right));
                    x2 = Math.Max(rect.Left, Math.Min(x2, rect.Right));
                    if (x2 - x1 < 4) x2 = rect.Right;
                    Color c = tp.IsLong ? ColorTranslator.FromHtml("#ef4444") : ColorTranslator.FromHtml("#22c55e");
                    using (var pen = new Pen(Color.FromArgb(130, c), 1.3f) { DashStyle = DashStyle.Dash })
                        gr.DrawLine(pen, x1, y, x2, y);   // scrolls with the chart now (not pinned to the screen)
                    string tl = (tp.IsLong ? "trapped longs " : "trapped shorts ") + tp.Vol;
                    float lx = Math.Max(rect.Left + 4, Math.Min(x1, rect.Right - 120));
                    using (var bg = new SolidBrush(Color.FromArgb(205, 0, 0, 0)))
                        gr.FillRectangle(bg, lx - 2, y - 13, gr.MeasureString(tl, _font).Width + 4, 13);
                    using (var br = new SolidBrush(c))
                        gr.DrawString(tl, _font, br, lx, y - 13);
                }
            }

            // REAL MBO icebergs/absorption — trade-anchored, from the backend detector (diamond at the exact price + time it absorbed)
            if (ShowMboIce && ice != null && ice.Length > 0)
            {
                foreach (var iv in ice)
                {
                    int x = X(iv.Time), y = Y(iv.Price);
                    if (x == int.MinValue || y == int.MinValue || x < rect.Left || x > rect.Right || y < rect.Top || y > rect.Bottom) continue;
                    int r = (int)Math.Max(4, Math.Min(13, 4 + Math.Sqrt(iv.Absorbed)));
                    if (iv.Sweep)
                    {
                        // WALL SWEPT (traded clean through) = BURST BUBBLE. aggressor = opposite the wall side:
                        // bid/support wall broken => sellers won (red/bearish); ask/resistance wall broken => buyers won (green/bullish)
                        Color sc = iv.IsBid ? ColorTranslator.FromHtml("#ef4444") : ColorTranslator.FromHtml("#22c55e");
                        int rr = r + 2;
                        using (var glow = new SolidBrush(Color.FromArgb(60, sc)))
                            gr.FillEllipse(glow, x - rr - 3, y - rr - 3, (rr + 3) * 2, (rr + 3) * 2);
                        using (var br = new SolidBrush(Color.FromArgb(230, sc)))
                            gr.FillEllipse(br, x - rr, y - rr, rr * 2, rr * 2);
                        using (var pen = new Pen(sc, 2f))
                            gr.DrawEllipse(pen, x - rr - 3, y - rr - 3, (rr + 3) * 2, (rr + 3) * 2);
                        using (var br2 = new SolidBrush(sc))
                            gr.DrawString("SWEEP " + iv.Absorbed.ToString("0"), _fontB, br2, x + rr + 3, y - 7);
                        continue;
                    }
                    if (iv.Pull)
                    {
                        // wall PULLED (cancelled, not eaten) = hollow ghost ring. support pulled=red(bearish) / resistance pulled=green(bullish)
                        Color pc = iv.IsBid ? ColorTranslator.FromHtml("#ef4444") : ColorTranslator.FromHtml("#22c55e");
                        int rr = r + 2;
                        using (var pen = new Pen(Color.FromArgb(210, pc), 1.6f) { DashStyle = DashStyle.Dash })
                            gr.DrawEllipse(pen, x - rr, y - rr, rr * 2, rr * 2);
                        using (var br2 = new SolidBrush(pc))
                            gr.DrawString("pull " + iv.Absorbed.ToString("0"), _font, br2, x + rr + 3, y - 7);
                        continue;
                    }
                    Color c = iv.IsBid ? ColorTranslator.FromHtml("#2dd4bf") : ColorTranslator.FromHtml("#fb923c");
                    if (iv.Iceberg)
                    {
                        // ICEBERG (hidden refiller) = DIAMOND
                        var pts = new[] { new Point(x, y - r), new Point(x + r, y), new Point(x, y + r), new Point(x - r, y) };
                        using (var glow = new SolidBrush(Color.FromArgb(70, c)))
                            gr.FillPolygon(glow, new[] { new Point(x, y - r - 2), new Point(x + r + 2, y), new Point(x, y + r + 2), new Point(x - r - 2, y) });
                        using (var br = new SolidBrush(Color.FromArgb(225, c)))
                            gr.FillPolygon(br, pts);
                        using (var pen = new Pen(Color.FromArgb(255, c), 1f))
                            gr.DrawPolygon(pen, pts);
                    }
                    else
                    {
                        // ABSORPTION (visible block held) = CIRCLE
                        using (var glow = new SolidBrush(Color.FromArgb(70, c)))
                            gr.FillEllipse(glow, x - r - 2, y - r - 2, (r + 2) * 2, (r + 2) * 2);
                        using (var br = new SolidBrush(Color.FromArgb(225, c)))
                            gr.FillEllipse(br, x - r, y - r, r * 2, r * 2);
                        using (var pen = new Pen(Color.FromArgb(255, c), 1f))
                            gr.DrawEllipse(pen, x - r, y - r, r * 2, r * 2);
                    }
                    using (var br2 = new SolidBrush(c))
                        gr.DrawString(iv.Absorbed.ToString("0"), _font, br2, x + r + 2, y - 7);
                }
            }

            // aggressive prints (triangles at time/price)
            if (false && ShowPrints && rs.Prints != null)   // DECLUTTER: aggressive-print bubbles OFF (flip false->true to restore)
            {
                double wallTol = (Symbol?.TickSize ?? 0.25) * 1.5;   // a print "hits" a wall if within ~1 tick of it
                foreach (var p in rs.Prints)
                {
                    int x = X(p.Time), y = Y(p.Price);
                    if (x == int.MinValue || y == int.MinValue || x < rect.Left || x > rect.Right) continue;
                    if (BubblesOnlyAtWalls && mw != null && mw.Length > 0)   // only gate when wall data exists; no walls -> don't suppress bubbles
                    {
                        bool atWall = false;
                        foreach (var w in mw) if (Math.Abs(w.Price - p.Price) <= wallTol) { atWall = true; break; }
                        if (!atWall) continue;   // not a wall hit -> no bubble (kills per-trade noise)
                    }
                    Color c = p.Buy ? ColorTranslator.FromHtml("#22c55e") : (p.Sell ? ColorTranslator.FromHtml("#ef4444") : Color.Gray);
                    if (BubbleMode)
                    {
                        int rad = (int)Math.Max(2, Math.Min(20, 1.8 + 1.5 * Math.Sqrt(p.Size)));   // bubble radius = trade size
                        int a = (int)Math.Min(195, 60 + p.Size * 2);                                // bigger trade = more opaque
                        using (var br = new SolidBrush(Color.FromArgb(a, c)))
                            gr.FillEllipse(br, x - rad, y - rad, rad * 2, rad * 2);
                        using (var pen = new Pen(Color.FromArgb(Math.Min(230, a + 50), c), 1f))
                            gr.DrawEllipse(pen, x - rad, y - rad, rad * 2, rad * 2);
                    }
                    else
                    {
                        int r = (int)Math.Min(11, 3 + Math.Sqrt(p.Size));
                        using (var br = new SolidBrush(Color.FromArgb(205, c)))
                        {
                            if (p.Sell) FillTriangle(gr, br, x, y, r, false);
                            else FillTriangle(gr, br, x, y, r, true);
                        }
                    }
                }
            }

            // EXHAUSTION model — every fire today, as a marker at the swept extreme (NQ only)
            if (ShowExhaustion && isNq && fires != null)
            {
                foreach (var fz in fires)
                {
                    if (!fz.Fired) continue;
                    int x = X(fz.Time), y = Y(fz.Price);
                    if (x == int.MinValue || y == int.MinValue || x < rect.Left || x > rect.Right) continue;
                    int a = fz.Strength == "strong" ? 235 : fz.Strength == "moderate" ? 190 : 140;
                    using (var br = new SolidBrush(Color.FromArgb(a, magenta)))
                    using (var tbr = new SolidBrush(Color.FromArgb(Math.Max(a, 200), magenta)))
                    {
                        // leg_dir +1 = fresh HIGH -> fade short -> DOWN arrow above the high
                        // leg_dir -1 = fresh LOW  -> fade long  -> UP arrow below the low
                        if (fz.LegDir > 0) FillTriangle(gr, br, x, y - 9, 6, false);
                        else FillTriangle(gr, br, x, y + 9, 6, true);
                        // clock time next to the marker (above a high, below a low)
                        string ft = Clock(fz.Time);
                        var fs = gr.MeasureString(ft, _font);
                        gr.DrawString(ft, _font, tbr, x - fs.Width / 2f, fz.LegDir > 0 ? y - 16 - fs.Height : y + 16);
                    }
                }
            }

            // EXHAUSTION model — CURRENT read (always shown while live; faint watch-line, bold dashed when fired) (NQ only)
            if (ShowExhaustion && isNq && exh != null && exh.Status == "live" && exh.EventPrice > 0)
            {
                int y = Y(exh.EventPrice);
                if (y != int.MinValue && y >= rect.Top && y <= rect.Bottom)
                {
                    bool fired = exh.Fired;
                    string dir = exh.LegDir > 0 ? "high" : "low";
                    using (var pen = new Pen(Color.FromArgb(fired ? 235 : 120, magenta), fired ? 2f : 1f) { DashStyle = fired ? DashStyle.Dash : DashStyle.Dot })
                        gr.DrawLine(pen, rect.Left, y, rect.Right, y);
                    string when = exh.EventTsMs > 0
                        ? "   " + Clock(DateTimeOffset.FromUnixTimeMilliseconds(exh.EventTsMs).UtcDateTime)
                          + (exh.MinutesAgo >= 0 ? " (" + exh.MinutesAgo + "m ago)" : "")
                        : "";
                    string label = (fired
                        ? "REVERSAL " + (exh.Prob * 100).ToString("0") + "%  " + (exh.Strength ?? "") + "  (" + dir + " exhausting)  @ " + exh.EventPrice.ToString("0.##")
                        : "rev watch  " + (exh.Prob * 100).ToString("0") + "%  (" + dir + ")  @ " + exh.EventPrice.ToString("0.##")) + when;
                    var sz = gr.MeasureString(label, fired ? _fontB : _font);
                    using (var bg = new SolidBrush(Color.FromArgb(fired ? 195 : 140, 0, 0, 0)))
                        gr.FillRectangle(bg, rect.Left + 4, y - 15, sz.Width + 6, 14);
                    using (var br = new SolidBrush(Color.FromArgb(fired ? 255 : 175, magenta)))
                        gr.DrawString(label, fired ? _fontB : _font, br, rect.Left + 6, y - 15);
                }
            }

            // FLOWING band — a moving-average centerline ± width.
            //   NQ:     width = the model's expected day-range (constant, the edge).
            //   off-NQ: width = BandSigma * rolling stddev (real Bollinger, breathes) — built from the asset's OWN bars.
            bool nqBand = isNq && exh != null && exh.RegimeStatus == "live" && !string.IsNullOrEmpty(exh.Regime) && exh.RegimeRangeT > 0;
            bool volBand = !isNq && ShowBandOffNq;
            if (false && ShowRangeBand && (nqBand || volBand))   // bands removed -> replaced by the Market State panel below
            {
                double tick = (Symbol != null && Symbol.TickSize > 0) ? Symbol.TickSize : 0.25;
                double nqHalf = nqBand ? (exh.RegimeRangeT / 2.0) * tick * (BandWidthPct / 100.0) : 0;
                int maLen = Math.Max(2, BandMaLength);
                int barCount = 0; try { barCount = Count; } catch { barCount = 0; }
                if (barCount > maLen)
                {
                    var up = new List<Point>(); var dn = new List<Point>(); var mid = new List<Point>();
                    for (int off = 0; off + maLen <= barCount; off++)
                    {
                        DateTime bt; try { bt = Time(off); } catch { break; }
                        int x = X(bt);
                        if (x == int.MinValue) continue;
                        if (x < rect.Left - 2) break;          // walked past the left edge of the viewport
                        if (x > rect.Right + 2) continue;
                        double sum = 0; for (int k = 0; k < maLen; k++) sum += Close(off + k);
                        double ma = sum / maLen;
                        double half;
                        if (nqBand) half = nqHalf;
                        else
                        {
                            double v = 0; for (int k = 0; k < maLen; k++) { double d = Close(off + k) - ma; v += d * d; }
                            half = BandSigma * Math.Sqrt(v / maLen) * (BandWidthPct / 100.0);   // ± k·σ, breathes per bar
                        }
                        if (half <= 0) continue;
                        int yM = Y(ma), yU = Y(ma + half), yD = Y(ma - half);
                        if (yM == int.MinValue || yU == int.MinValue || yD == int.MinValue) continue;
                        mid.Add(new Point(x, yM)); up.Add(new Point(x, yU)); dn.Add(new Point(x, yD));
                    }
                    if (up.Count >= 2)
                    {
                        Color bc; string lbl;
                        if (nqBand)
                        {
                            string brg = exh.Regime.ToUpperInvariant();
                            bc = brg == "HI" ? ColorTranslator.FromHtml("#f87171") : brg == "MID" ? ColorTranslator.FromHtml("#eab308") : ColorTranslator.FromHtml("#2dd4bf");
                            lbl = "exp " + brg + " band  +/-" + (exh.RegimeRangeT / 2.0 * (BandWidthPct / 100.0)).ToString("0") + "t";
                        }
                        else
                        {
                            bc = ColorTranslator.FromHtml("#60a5fa");   // blue = per-asset volatility band (NOT the NQ model)
                            lbl = (Symbol?.Name ?? "vol") + " band  " + BandSigma.ToString("0.#") + "σ";
                        }
                        var poly = new List<Point>(up);
                        for (int i = dn.Count - 1; i >= 0; i--) poly.Add(dn[i]);
                        using (var fill = new SolidBrush(Color.FromArgb(18, bc)))
                            gr.FillPolygon(fill, poly.ToArray());
                        using (var penB = new Pen(Color.FromArgb(175, bc), 1.4f))
                        {
                            gr.DrawLines(penB, up.ToArray());
                            gr.DrawLines(penB, dn.ToArray());
                        }
                        using (var penM = new Pen(Color.FromArgb(90, bc), 1f) { DashStyle = DashStyle.Dot })
                            gr.DrawLines(penM, mid.ToArray());
                        using (var br = new SolidBrush(bc))
                            gr.DrawString(lbl, _fontB, br, Math.Max(rect.Left + 4, up[0].X - 150), up[0].Y - 14);
                    }
                }
            }

            // MARKET STATE panel (top-center) — gamma profile (per-asset) + vol regime. Replaces the band + old banner.
            if (ShowMarketState)
            {
                var gm = _gamma;
                var msl = new List<(string, Color)>();
                Color cRed = ColorTranslator.FromHtml("#f87171");
                Color cTeal = ColorTranslator.FromHtml("#2dd4bf");
                Color cYel = ColorTranslator.FromHtml("#eab308");
                Color cDim = Color.FromArgb(205, 148, 163, 184);
                double livePx = 0; try { livePx = Close(0); } catch { }
                if (livePx <= 0 && gm != null) livePx = gm.PanelPx;

                if (gm != null && gm.Ok && livePx > 0)
                {
                    bool neg = livePx < gm.Flip; double d = livePx - gm.Flip;
                    msl.Add(("GAMMA  " + (neg ? "NEGATIVE" : "POSITIVE") + "   flip " + gm.Flip.ToString("0") + "  (" + (d >= 0 ? "+" : "") + d.ToString("0") + ")", neg ? cRed : cTeal));
                    string lv = "";
                    if (gm.CallWall > 0) lv += "ceil " + gm.CallWall.ToString("0") + "    ";
                    if (gm.MaxPain > 0) lv += "pin " + gm.MaxPain.ToString("0") + "    ";
                    if (gm.GexNeg > 0) lv += "accel " + gm.GexNeg.ToString("0");
                    if (lv.Length > 0) msl.Add((lv.TrimEnd(), cDim));
                }
                if (isNq && exh != null && exh.RegimeStatus == "live" && !string.IsNullOrEmpty(exh.Regime))
                {
                    string rg = exh.Regime.ToUpperInvariant();
                    Color rc = rg == "HI" ? cRed : rg == "MID" ? cYel : cTeal;
                    double tk = (Symbol != null && Symbol.TickSize > 0) ? Symbol.TickSize : 0.25;
                    msl.Add(("VOL  " + rg + "   exp ~" + (exh.RegimeRangeT * tk).ToString("0") + " pts/day  (" + exh.RegimeRangeT.ToString("0") + "t)", rc));
                }
                if (msl.Count > 0)
                {
                    var tsz = gr.MeasureString("MARKET STATE", _fontReg);
                    float pw = tsz.Width, ph = tsz.Height + 2;
                    foreach (var (t, _) in msl) { var s = gr.MeasureString(t, _fontB); if (s.Width > pw) pw = s.Width; ph += s.Height; }
                    float px2 = rect.Left + (rect.Width - pw) / 2f, py2 = rect.Top + 4;
                    using (var bg = new SolidBrush(Color.FromArgb(185, 0, 0, 0)))
                        gr.FillRectangle(bg, px2 - 12, py2, pw + 24, ph + 8);
                    using (var hb = new SolidBrush(Color.FromArgb(235, 226, 232, 240)))
                        gr.DrawString("MARKET STATE", _fontReg, hb, px2, py2 + 3);
                    float yy2 = py2 + 3 + tsz.Height + 1;
                    foreach (var (t, col) in msl)
                    {
                        using (var br2 = new SolidBrush(col)) gr.DrawString(t, _fontB, br2, px2, yy2);
                        yy2 += gr.MeasureString(t, _fontB).Height;
                    }
                }
            }

            // summary panel (top-right, away from the gamma indicator's top-left panel)
            var lines = new List<(string, Color)>();
            lines.Add(("InSync Orderflow", Color.FromArgb(235, 226, 232, 240)));
            if (rs.HasImb)
            {
                double im = rs.Imbalance;
                if (im >= 1) lines.Add(("Imbalance  " + im.ToString("0.0") + "x bid", ColorTranslator.FromHtml("#22c55e")));
                else lines.Add(("Imbalance  " + (im > 0 ? 1 / im : 0).ToString("0.0") + "x ask", ColorTranslator.FromHtml("#ef4444")));
            }
            int iceN = rs.Walls?.Count(w => w.Iceberg) ?? 0;
            int absN = rs.Walls?.Count(w => w.Absorption) ?? 0;
            lines.Add(("walls " + (rs.Walls?.Count ?? 0) + "  ice " + iceN + "  abs " + absN, Color.FromArgb(215, 148, 163, 184)));
            if (AutoScale)
                lines.Add(("scale: wall>=" + _effWall.ToString("0") + "  print>=" + _effBigPrint.ToString("0"), Color.FromArgb(150, 148, 163, 184)));
            if (ShowExhaustion && isNq && exh != null)
            {
                int firedToday = fires?.Count(fz => fz.Fired) ?? 0;
                bool fired = exh.Fired;
                string es = exh.Status != "live" ? "exhaustion: " + (exh.Status ?? "-")
                          : fired ? "exhaustion: REV " + (exh.Prob * 100).ToString("0") + "% " + (exh.Strength ?? "")
                          : "exhaustion: watch " + (exh.Prob * 100).ToString("0") + "%";
                lines.Add((es + "  (" + firedToday + " fired today)", fired ? magenta : Color.FromArgb(195, 148, 163, 184)));
            }
            else if (!isNq)
                lines.Add(("model: NQ only · order-flow auto-scaled", Color.FromArgb(170, 148, 163, 184)));
            DrawPanelRight(gr, rect, lines);
        }

        private static void FillTriangle(Graphics gr, Brush br, int x, int y, int r, bool up)
        {
            Point[] pts = up
                ? new[] { new Point(x, y - r), new Point(x - r, y + r), new Point(x + r, y + r) }
                : new[] { new Point(x, y + r), new Point(x - r, y - r), new Point(x + r, y - r) };
            gr.FillPolygon(br, pts);
        }

        private void DrawPanelRight(Graphics gr, Rectangle rect, List<(string text, Color col)> lines)
        {
            float w = 0, h = 0;
            foreach (var (t, _) in lines) { var sz = gr.MeasureString(t, _font); if (sz.Width > w) w = sz.Width; h += sz.Height; }
            float left = rect.Right - w - 14;
            using (var bg = new SolidBrush(Color.FromArgb(150, 0, 0, 0)))
                gr.FillRectangle(bg, left - 4, rect.Top + 4, w + 12, h + 6);
            float yy = rect.Top + 6;
            foreach (var (t, col) in lines)
            {
                using (var br = new SolidBrush(col)) gr.DrawString(t, _font, br, left, yy);
                yy += gr.MeasureString(t, _font).Height;
            }
        }

        private sealed class Lvl
        {
            public double CurSize, MaxSize, Traded, TradedRecent;
            public int Orders;
            public bool IsBid;
            public DateTime LastTrade;
        }
        private sealed class Wall { public double Price, Size, Eaten; public bool IsBid, Iceberg, Absorption; }
        private sealed class Ghost { public double Price, PeakSize, PeakEaten; public bool IsBid, Iceberg, Absorption; public int AgeSec; }
        private sealed class Mark { public double Price, PeakSize, PeakEaten; public bool IsBid, Iceberg, Absorption, LiveNow; public DateTime LastActive; }
        private sealed class GammaState { public bool Ok; public double Flip, CallWall, GexNeg, MaxPain, PanelPx; }
        private sealed class IceFlow { public DateTime Time; public double Price, Absorbed; public bool IsBid, Iceberg, Sweep, Pull; }
        private sealed class MboWall { public double Price, Size; public int Orders, Filled, Cancelled; public string Side; }
        private sealed class TrapLevel { public double Price; public int Vol; public bool IsLong; public DateTime Time; }
        private sealed class FlowBar { public DateTime Time; public double Fill, Cancel, BullFill, SellFill; }
        private sealed class FillMark { public DateTime Time; public double Price; public string Side; public int Filled; }
        private sealed class Print { public DateTime Time; public double Price, Size; public bool Buy, Sell; }
        private sealed class Fire { public DateTime Time; public double Price, Prob, Exhaust; public int LegDir; public bool Fired; public string Strength; }
        private sealed class RenderState
        {
            public List<Wall> Walls = new List<Wall>();
            public List<Ghost> GhostLevels = new List<Ghost>();
            public List<Print> Prints = new List<Print>();
            public double Imbalance, BidSum, AskSum;
            public bool HasImb;
        }
        private sealed class ExhState
        {
            public bool Fired;
            public double Prob, Exhaust, EventPrice;
            public int LegDir;
            public long EventTsMs;
            public int MinutesAgo = -1;
            public string Strength, Status;
            public string Regime, RegimeStatus;
            public double RegimeRangeT, RegimeAnchor;
        }
    }
}
