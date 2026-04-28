import PageHeader from "@/components/PageHeader";

export default function BacktestDetailLoading() {
 return (
 <div className="pb-10">
 <div className="px-6 pt-4">
 <span className="inline-block h-6 w-24 animate-pulse bg-surface-alt" />
 </div>
 <PageHeader title="Loading…" description="Fetching run, trades, equity, metrics" />
 <div className="flex flex-col gap-4 px-8">
 <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
 {Array.from({ length: 12 }).map((_, i) => (
 <div
 key={i}
 className="h-[74px] animate-pulse rounded-lg border border-border bg-surface"
 />
 ))}
 </div>
 <div className="h-[288px] animate-pulse rounded-lg border border-border bg-surface" />
 <div className="h-[400px] animate-pulse rounded-lg border border-border bg-surface" />
 </div>
 </div>
 );
}
