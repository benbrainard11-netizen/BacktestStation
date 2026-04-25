import MockDataBanner from "@/components/prop-simulator/MockDataBanner";

export default function PropSimulatorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="bg-depth-grid bg-depth-radial">
      <MockDataBanner />
      {children}
    </div>
  );
}
