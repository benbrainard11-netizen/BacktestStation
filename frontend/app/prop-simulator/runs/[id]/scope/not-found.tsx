import Btn from "@/components/ui/Btn";

export default function ScopeNotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="text-[10px] tracking-[0.5em] text-text-mute">
        Tearsheet · run not found
      </p>
      <h1 className="text-2xl font-light text-text">No such simulation.</h1>
      <Btn href="/prop-simulator/runs">← All runs</Btn>
    </div>
  );
}
