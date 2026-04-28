"use client";

import Panel from "@/components/Panel";
import StatusDot, { type StatusTone } from "@/components/StatusDot";
import type { components } from "@/lib/api/generated";

type Task = components["schemas"]["ScheduledTaskStatus"];

interface Props {
 tasks: Task[];
 supported: boolean;
}

export default function ScheduledTasksPanel({ tasks, supported }: Props) {
 if (!supported) {
 return (
 <Panel title="Scheduled tasks" meta="not supported">
 <p className="tabular-nums text-xs text-text-mute">
 Windows Scheduled Task introspection is only available on
 Windows hosts. This appears to be running elsewhere.
 </p>
 </Panel>
 );
 }

 if (tasks.length === 0) {
 return (
 <Panel title="Scheduled tasks" meta="none registered">
 <p className="tabular-nums text-xs text-text-mute">
 No BacktestStation scheduled tasks were found on this host. Run{" "}
 <code className="text-text-dim">scripts/install_scheduled_tasks.ps1</code>
 {" "}to register them.
 </p>
 </Panel>
 );
 }

 return (
 <Panel title="Scheduled tasks" meta={`${tasks.length} registered`}>
 <div className="overflow-x-auto">
 <table className="w-full tabular-nums text-xs">
 <thead>
 <tr className="text-left text-[10px] text-text-mute">
 <th className="pb-2 pr-4">Task</th>
 <th className="pb-2 pr-4">Result</th>
 <th className="pb-2 pr-4">Last run (local)</th>
 <th className="pb-2 pr-4">Next run (local)</th>
 <th className="pb-2 pr-4">State</th>
 </tr>
 </thead>
 <tbody>
 {tasks.map((t) => (
 <TaskRow key={t.name} task={t} />
 ))}
 </tbody>
 </table>
 </div>
 </Panel>
 );
}

function TaskRow({ task }: { task: Task }) {
 const tone = labelToTone(task.last_result_label);
 const labelClass =
 task.last_result_label === "ok"
 ? "text-pos"
 : task.last_result_label === "failed"
 ? "text-neg"
 : task.last_result_label === "never_run"
 ? "text-text-mute"
 : "text-text-dim";

 return (
 <tr className="border-t border-border">
 <td className="py-2 pr-4 text-text">{task.name}</td>
 <td className="py-2 pr-4">
 <span className="flex items-center gap-2">
 <StatusDot status={tone} />
 <span className={` text-[10px] ${labelClass}`}>
 {task.last_result_label}
 </span>
 {task.last_result !== null && task.last_result !== undefined && task.last_result !== 0
 ? <span className="text-neg tabular-nums">(rc={task.last_result})</span>
 : null}
 </span>
 </td>
 <td className="py-2 pr-4 text-text-dim tabular-nums">
 {formatLocal(task.last_run_ts)}
 </td>
 <td className="py-2 pr-4 text-text-dim tabular-nums">
 {formatLocal(task.next_run_ts)}
 </td>
 <td className="py-2 pr-4 text-text-dim">{task.state ?? "—"}</td>
 </tr>
 );
}

function labelToTone(label: string): StatusTone {
 if (label === "ok") return "live";
 if (label === "failed") return "off";
 if (label === "never_run") return "idle";
 return "idle";
}

function formatLocal(iso: string | null | undefined): string {
 if (iso === null || iso === undefined) return "—";
 const d = new Date(iso);
 if (Number.isNaN(d.getTime())) return iso;
 return d.toLocaleString(undefined, {
 year: "numeric",
 month: "2-digit",
 day: "2-digit",
 hour: "2-digit",
 minute: "2-digit",
 hour12: false,
 });
}
