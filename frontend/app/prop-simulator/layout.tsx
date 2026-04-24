import MockDataBanner from "@/components/prop-simulator/MockDataBanner";

export default function PropSimulatorLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div>
      <MockDataBanner />
      {children}
    </div>
  );
}
