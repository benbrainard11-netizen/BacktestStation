// Diagonal "MOCK" watermark — like the DRAFT stamp on a draft tear sheet.
// Sits behind the content at very low opacity so it's discoverable on
// careful inspection but doesn't fight legibility.

export default function MockWatermark() {
 return (
 <div
 aria-hidden="true"
 className="pointer-events-none absolute inset-0 flex select-none items-center justify-center overflow-hidden"
 >
 <span
 className="block -rotate-12 whitespace-nowrap font-extralight tracking-[0.6em] text-text/[0.025]"
 style={{ fontSize: "clamp(8rem, 22vw, 22rem)" }}
 >
 MOCK · MOCK · MOCK
 </span>
 </div>
 );
}
