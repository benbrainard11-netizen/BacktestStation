"use client";

import Link from "next/link";

import type { components } from "@/lib/api/generated";

type RiskProfile = components["schemas"]["RiskProfileRead"];

interface Props {
  profiles: RiskProfile[];
}

export default function RiskProfileList({ profiles }: Props) {
  if (profiles.length === 0) {
    return (
      <p className="font-mono text-xs text-zinc-500">No profiles yet.</p>
    );
  }
  return (
    <div className="border border-zinc-800">
      <table className="w-full font-mono text-xs">
        <thead className="bg-zinc-950/60">
          <tr className="border-b border-zinc-800 text-left uppercase tracking-widest text-[10px] text-zinc-500">
            <Th>Name</Th>
            <Th>Status</Th>
            <Th>Daily loss cap</Th>
            <Th>DD cap</Th>
            <Th>Strategy params</Th>
            <Th>Updated</Th>
            <Th>{""}</Th>
          </tr>
        </thead>
        <tbody>
          {profiles.map((p) => (
            <tr
              key={p.id}
              className="border-b border-zinc-900 last:border-b-0 hover:bg-zinc-950/40"
            >
              <Td>
                <Link
                  href={`/risk-profiles/${p.id}`}
                  className="text-zinc-100 underline-offset-2 hover:underline"
                >
                  {p.name}
                </Link>
              </Td>
              <Td>{p.status}</Td>
              <Td>{p.max_daily_loss_r === null ? "—" : `${p.max_daily_loss_r}R`}</Td>
              <Td>{p.max_drawdown_r === null ? "—" : `${p.max_drawdown_r}R`}</Td>
              <Td>
                {p.strategy_params
                  ? Object.keys(p.strategy_params).length
                  : 0}{" "}
                key(s)
              </Td>
              <Td>
                {p.updated_at
                  ? new Date(String(p.updated_at)).toLocaleString()
                  : "—"}
              </Td>
              <Td>
                <Link
                  href={`/risk-profiles/${p.id}`}
                  className="text-zinc-400 underline-offset-2 hover:text-zinc-100 hover:underline"
                >
                  edit →
                </Link>
              </Td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return <th className="px-3 py-2">{children}</th>;
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-3 py-2">{children}</td>;
}
