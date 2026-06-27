import json, time, os, datetime as dt, sys
# our own dir (mbo_analysis) ships an inspect.py probe that SHADOWS stdlib `inspect`; since `import zmq`
# pulls in inspect, drop our dir from sys.path first or the PUB import silently fails (no live stream).
_self_dir=os.path.dirname(os.path.abspath(__file__))
sys.path[:]=[p for p in sys.path if os.path.abspath(p or ".")!=_self_dir]
OUT_DIR=r"D:\data\heartbeat"; OUT=os.path.join(OUT_DIR,"iceberg_flow.json")
# LIVE PUSH: publish the derived walls/fills/flow on a ZMQ PUB socket so the chart can STREAM (long-poll) instead of file-polling.
# Fail-safe: if zmq is missing or the port is busy, _pub stays None and the detector runs exactly as before (file-only).
PUB_ADDR="tcp://127.0.0.1:5862"
try:
    import zmq
    _pub=zmq.Context.instance().socket(zmq.PUB); _pub.setsockopt(zmq.SNDHWM,4); _pub.bind(PUB_ADDR)
except Exception:
    _pub=None
def publish(payload):
    if _pub is None: return
    try: _pub.send_string(json.dumps(payload))
    except Exception: pass
MBO_DIR=r"D:\data\raw\live\rithmic_mbo"
GAP_NS=8_000_000_000
MIN_VOL={"NQ.c.0":15,"ES.c.0":100,"RTY.c.0":20}; DEFAULT_MIN=25
EVENT_TTL_SEC=7200; WRITE_EVERY=0.1   # build/publish/snapshot ~10x/sec: ZMQ push (stream) is near-instant; file is the fallback/REST source
ICE_RATIO=3.0  # absorbed >= ICE_RATIO x peak resting depth => hidden refiller (iceberg), else block absorption
WARM_BYTES=600_000_000  # on startup, replay this much tail first so the order book + recent history are warm (not cold)
WALL_MIN={"NQ.c.0":45,"ES.c.0":150,"RTY.c.0":80}; DEFAULT_WALL=60  # peak resting depth >= this => a tracked "wall" (set from measured ~top 1-3% of levels)
SWEEP_FRAC=0.25  # wall counts as GONE when current rest < SWEEP_FRAC x peak
FILL_FRAC=0.5    # ...and SWEPT (vs just pulled/cancelled) only if trades ate >= FILL_FRAC x peak
WALL_SHOW_MIN=15 # min resting size to ever show as a wall (absolute floor; also gated to >=40% of the symbol's top level)
TRAP_MIN={"NQ.c.0":15,"ES.c.0":50,"RTY.c.0":20}; DEFAULT_TRAP=25        # min trapped aggressive size to flag
TRAP_DIST={"NQ.c.0":120,"ES.c.0":40,"RTY.c.0":25}; DEFAULT_TRAP_DIST=40 # only flag traps within this distance of price (near-term S/R)
TRAP_GAP_NS=60_000_000_000  # price away from a level >60s = a fresh visit -> reset that level's trapped tally
PULL_MIN={"NQ.c.0":50,"ES.c.0":150,"RTY.c.0":80}; DEFAULT_PULL=60   # flag a PULL only for walls >= this peak that collapse by CANCEL (not eaten)
def today_file():
    d=dt.datetime.now(dt.timezone.utc).date().isoformat()
    return os.path.join(MBO_DIR,f"RITHMIC-mbo-{d}.jsonl")
side_at={}; orders={}; rest={}; ocount={}; wall={}; epi={}; events=[]; feed_now=[0]
last_px={}; last_dir={}; trap={}; flow={}; fillmark={}   # ...trap[(s,p)]=[abuy,asell,last_ts]; flow[(s,minute)]=[bull_fill,sell_fill,removed]; fillmark[(s,price,minute)]=[filled,side] for the on-candle +N/-N markers
FILLMARK_MIN={"NQ.c.0":2,"ES.c.0":10,"RTY.c.0":3}; DEFAULT_FILLMARK=3   # min filled (per price, per minute) to plot a +N/-N marker. fills are RARE (walls mostly pull) so keep this low or nothing shows
STALE_BUF={"NQ.c.0":1.0,"ES.c.0":1.0,"RTY.c.0":0.5}; DEFAULT_STALE_BUF=1.0   # drop a resting ASK this far BELOW last trade / BID this far ABOVE = phantom level left by an untracked pre-warmup order (can't be on that side of the market)
def thresh(s): return MIN_VOL.get(s,DEFAULT_MIN)
def wmin(s): return WALL_MIN.get(s,DEFAULT_WALL)
def trap_min(s): return TRAP_MIN.get(s,DEFAULT_TRAP)
def trap_dist(s): return TRAP_DIST.get(s,DEFAULT_TRAP_DIST)
def pull_min(s): return PULL_MIN.get(s,DEFAULT_PULL)
def add_flow(s,ts,fill,removed,side=None):   # per-minute wall flow: bid-wall fills (bull-limit hit), ask-wall fills (sell-limit hit), removed
    bk=(s, ts//60_000_000_000); fl=flow.get(bk)
    if fl is None: fl=[0,0,0]; flow[bk]=fl    # [bull_fill, sell_fill, removed]
    if fill>0:
        if side=="A": fl[1]+=fill             # ask wall traded = a SELL limit got hit
        else: fl[0]+=fill                     # bid wall (or unknown) traded = a BULL limit got hit
    fl[2]+=removed
def add_fillmark(s,p,ts,sz,side):   # accumulate filled size per (price, minute) so the chart can print +N/-N on the candle that filled it
    bk=(s,p,ts//60_000_000_000); fm=fillmark.get(bk)
    if fm is None: fm=[0,side if side in ("B","A") else "?"]; fillmark[bk]=fm
    fm[0]+=sz
    if side in ("B","A"): fm[1]=side
def note_wall(s,p):
    # resting depth at this price crossed the wall threshold -> track it (peak size + resting side)
    rsz=rest.get((s,p),0)
    if rsz>=wmin(s):
        w=wall.get((s,p))
        if w is None: wall[(s,p)]={"peak":rsz,"traded":0,"removed":0,"side":side_at.get((s,p),"?")}
        elif rsz>w["peak"]: w["peak"]=rsz; w["side"]=side_at.get((s,p),w["side"])
def check_sweep(s,p):
    # resting depth just dropped: a wall that's now gone AND was eaten by trades = SWEPT (emit a bubble)
    w=wall.get((s,p))
    if not w: return
    if rest.get((s,p),0) < SWEEP_FRAC*w["peak"]:
        if w["traded"] >= FILL_FRAC*w["peak"]:
            events.append({"symbol":s,"side":w["side"],"price":p,"absorbed":int(w["peak"]),
                "filled":int(w["traded"]),"kind":"sweep","shown":int(w["peak"]),"dur_s":0.0,
                "ts_ms":int(feed_now[0]/1e6)})
        elif w["peak"]>=pull_min(s):   # collapsed by CANCEL, not eaten = PULLED (liquidity yanked)
            events.append({"symbol":s,"side":w["side"],"price":p,"absorbed":int(w["peak"]),
                "filled":int(w["traded"]),"kind":"pull","shown":int(w["peak"]),"dur_s":0.0,
                "ts_ms":int(feed_now[0]/1e6)})
        del wall[(s,p)]
def finalize(k,e):
    s,p=k
    if e["vol"]>=thresh(s):
        pd=e.get("peak_disp",0)
        kind="iceberg" if (pd>0 and e["vol"]>=ICE_RATIO*pd) else "absorption"
        sv=e.get("sellv",0); bv=e.get("buyv",0)
        side=("B" if sv>bv else "A") if sv!=bv else side_at.get((s,p),"?")   # AGGRESSOR: more sells=bid(teal)/more buys=ask(orange); tie or no tick-info -> resting side (avoids false teal)
        events.append({"symbol":s,"side":side,"price":p,"absorbed":int(e["vol"]),
            "shown":int(pd),"kind":kind,
            "dur_s":round((e["last_ts"]-e["start_ts"])/1e9,1),"ts_ms":int(e["last_ts"]/1e6)})
def on_book(r):
    # maintain per-order book so rest[(sym,price)] = TRUE aggregate resting size at that price
    a=r.get("action");s=r.get("symbol");sd=r.get("side");p=r.get("price");oid=r.get("order_id");sz=r.get("size") or 0
    if a=="A":
        if p is None: return
        side_at[(s,p)]=sd
        if oid is not None: orders[oid]=(s,p,sz)
        rest[(s,p)]=rest.get((s,p),0)+sz
        ocount[(s,p)]=ocount.get((s,p),0)+1
        note_wall(s,p)
    elif a=="C":
        if oid is not None and oid in orders:
            o=orders.pop(oid); k2=(o[0],o[1]); rest[k2]=max(0,rest.get(k2,0)-o[2]); ocount[k2]=max(0,ocount.get(k2,0)-1)
            wc=wall.get(k2)
            if wc is not None:
                wc["removed"]=wc.get("removed",0)+o[2]   # order left the book (fill or cancel; cancel = removed - traded)
                add_flow(k2[0], r.get("ts_event") or feed_now[0], 0, o[2])
            check_sweep(*k2)
        elif p is not None:                  # untracked cancel (order added before our window)
            wc=wall.get((s,p))               # leave rest/ocount alone (would corrupt them), BUT count it toward the wall's
            if wc is not None:               # pulled total so fill/cancel is accurate instead of undercounted
                wc["removed"]=wc.get("removed",0)+sz
                add_flow(s, r.get("ts_event") or feed_now[0], 0, sz)
    elif a=="M":
        if oid is not None and oid in orders:   # remove old footprint first
            o=orders[oid]; k2=(o[0],o[1]); rest[k2]=max(0,rest.get(k2,0)-o[2]); ocount[k2]=max(0,ocount.get(k2,0)-1)
            wm=wall.get(k2)
            if wm is not None:
                wm["removed"]=wm.get("removed",0)+o[2]   # modified away = left this level
                add_flow(k2[0], r.get("ts_event") or feed_now[0], 0, o[2])
            check_sweep(*k2)
        if p is None: return
        side_at[(s,p)]=sd
        if oid is not None: orders[oid]=(s,p,sz)
        rest[(s,p)]=rest.get((s,p),0)+sz
        ocount[(s,p)]=ocount.get((s,p),0)+1
        note_wall(s,p)
def on_trade(r):
    s=r.get("symbol");p=r.get("price");sz=r.get("size") or 0;ts=r.get("ts_event") or 0
    if p is None or sz<=0: return
    lp=last_px.get(s); ld=last_dir.get(s,0)
    dt=0 if lp is None else (1 if p>lp else (-1 if p<lp else ld))   # tick test: uptick=buy, downtick=sell, carry through flats
    last_px[s]=p; last_dir[s]=dt
    k=(s,p); e=epi.get(k); d=rest.get(k,0)
    tr=trap.get(k)                                   # aggressive vol at this price since the last visit (trapped-trader tally)
    if tr is None or ts-tr[2]>TRAP_GAP_NS: tr=[0,0,ts]; trap[k]=tr
    if dt>0: tr[0]+=sz
    elif dt<0: tr[1]+=sz
    tr[2]=ts
    w=wall.get(k)
    if w is not None: w["traded"]+=sz; add_flow(s, ts, sz, 0, w.get("side")); add_fillmark(s, p, ts, sz, w.get("side"))   # credit trades against a wall + per-minute fill flow (by side) + on-candle marker
    if e and (ts-e["last_ts"])<=GAP_NS:
        e["vol"]+=sz; e["last_ts"]=ts
        if dt>0: e["buyv"]+=sz
        elif dt<0: e["sellv"]+=sz
        if d>e["peak_disp"]: e["peak_disp"]=d
    else:
        if e: finalize(k,e)
        epi[k]={"vol":sz,"start_ts":ts,"last_ts":ts,"buyv":sz if dt>0 else 0,"sellv":sz if dt<0 else 0,"peak_disp":d}
def handle(r):
    if r.get("event_type")=="trade": on_trade(r)
    else: on_book(r)
    t=r.get("ts_event") or 0
    if t>feed_now[0]: feed_now[0]=t
def write_out():
    fn=feed_now[0]
    for k in [k for k,e in epi.items() if fn-e["last_ts"]>GAP_NS]: finalize(k,epi.pop(k))
    now_ms=time.time()*1000; cutoff=now_ms-EVENT_TTL_SEC*1000
    events[:]=[ev for ev in events if ev["ts_ms"]>=cutoff]
    for k in [k for k,v in rest.items() if v<=0]: del rest[k]; ocount.pop(k,None); side_at.pop(k,None)   # prune emptied levels (bounds rest/ocount/side_at together)
    if len(side_at)>40000: side_at.clear()
    if len(orders)>2000000: orders.clear(); rest.clear(); wall.clear(); ocount.clear()
    if len(wall)>50000: wall.clear()
    # PHANTOM-LEVEL CLEANUP: a resting ASK can't sit below the last trade, nor a BID above it (it would have executed).
    # orders resting before our warmup window are untracked, so their cancel/fill can't decrement rest -> they linger as stale walls; prune by price here.
    stale=[]
    for k in rest:
        cp=last_px.get(k[0])
        if cp is None: continue
        sd=side_at.get(k); buf=STALE_BUF.get(k[0],DEFAULT_STALE_BUF)
        if (sd=="A" and k[1]<cp-buf) or (sd=="B" and k[1]>cp+buf): stale.append(k)
    for k in stale: rest.pop(k,None); ocount.pop(k,None); side_at.pop(k,None); wall.pop(k,None)
    # current biggest resting WALLS per symbol (auto-scaled: >= 40% of that symbol's top level, max 8 each)
    bysym={}
    for (s,p),v in rest.items(): bysym.setdefault(s,[]).append((p,v))
    walls_out=[]
    for s,lst in bysym.items():
        mx=max(v for _,v in lst)
        floor=max(WALL_SHOW_MIN,0.4*mx)
        for p,v in sorted([pv for pv in lst if pv[1]>=floor],key=lambda x:-x[1])[:8]:
            wv=wall.get((s,p)); fl=int(wv["traded"]) if wv else 0; cn=int(max(0,wv.get("removed",0)-wv["traded"])) if wv else 0  # filled=traded; cancelled=removed-traded
            walls_out.append({"symbol":s,"side":side_at.get((s,p),"?"),"price":p,"size":int(v),"orders":int(ocount.get((s,p),0)),"filled":fl,"cancelled":cn})
    # TRAPPED traders: aggressive vol now offside -> bought ABOVE price (trapped longs=resistance) or sold BELOW (trapped shorts=support)
    for k2 in [k2 for k2,tr in trap.items() if fn-tr[2]>7_200_000_000_000]: del trap[k2]   # drop levels untouched >2h
    if len(trap)>200000: trap.clear()
    tbysym={}
    for (s,p),tr in trap.items():
        cp=last_px.get(s)
        if cp is None: continue
        if cp<p and tr[0]>=trap_min(s) and (p-cp)<=trap_dist(s):
            tbysym.setdefault(s,[]).append((p,tr[0],"trap_long",round(p-cp,2),tr[2]))
        elif cp>p and tr[1]>=trap_min(s) and (cp-p)<=trap_dist(s):
            tbysym.setdefault(s,[]).append((p,tr[1],"trap_short",round(cp-p,2),tr[2]))
    traps_out=[]
    for s,lst in tbysym.items():
        for p,v,kd,dist,tts in sorted(lst,key=lambda x:-x[1])[:6]:
            traps_out.append({"symbol":s,"price":p,"vol":int(v),"kind":kd,"dist":dist,"ts_ms":int(tts/1e6)})
    # per-minute fill/cancel flow at tracked walls (for the histogram strip)
    nfb=fn//60_000_000_000
    for bk in [bk for bk in flow if nfb-bk[1]>140]: del flow[bk]   # keep ~140 minutes
    flow_out=[{"symbol":s,"ts_ms":int(b*60000),"bull_fill":int(fl[0]),"sell_fill":int(fl[1]),"fill":int(fl[0]+fl[1]),"cancel":int(max(0,fl[2]-fl[0]-fl[1]))} for (s,b),fl in flow.items()]
    # per-(price, minute) FILL markers: +N (bid/bull-limit) / -N (ask/sell-limit) drawn on the candle that filled the wall
    for bk in [bk for bk in fillmark if nfb-bk[2]>140]: del fillmark[bk]   # keep ~140 minutes
    if len(fillmark)>200000: fillmark.clear()
    fillmarks_out=[{"symbol":s,"price":p,"ts_ms":int(mn*60000),"side":fm[1],"filled":int(fm[0])}
                   for (s,p,mn),fm in fillmark.items() if fm[0]>=FILLMARK_MIN.get(s,DEFAULT_FILLMARK)]
    payload={"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),"status":"live","count":len(events),
        "walls":walls_out,"traps":traps_out,"flow":flow_out,"fillmarks":fillmarks_out,"events":sorted(events,key=lambda e:-e["absorbed"])[:200]}
    publish(payload)   # PUSH to live subscribers (the chart stream) first — near-instant
    tmp=OUT+".tmp"
    with open(tmp,"w") as f: json.dump(payload,f)
    os.replace(tmp,OUT)
def main():
    os.makedirs(OUT_DIR,exist_ok=True); path=today_file()
    while not os.path.exists(path): time.sleep(1); path=today_file()
    f=open(path,"r")
    _sz=os.path.getsize(path); f.seek(max(0,_sz-WARM_BYTES))
    if _sz>WARM_BYTES: f.readline()  # drop partial first line
    cur=path; last=0; warm=False
    print("iceberg_flow TRADE-ANCHORED live, warming book from tail of",os.path.basename(cur),flush=True)
    while True:
        line=f.readline()
        if line:
            try: handle(json.loads(line))
            except: pass
        else:
            if not warm:   # first time we hit live EOF = book is warm. only NOW start emitting, so a restart
                warm=True  # doesn't flash the chart through historical warmup-replay states (different walls each frame)
                print("iceberg_flow warm — going live (output enabled)",flush=True)
            np=today_file()
            if np!=cur and os.path.exists(np): f.close(); f=open(np,"r"); cur=np
            time.sleep(0.03)
        now=time.time()
        if warm and now-last>=WRITE_EVERY:
            try: write_out()
            except: pass
            last=now
if __name__=="__main__": main()
