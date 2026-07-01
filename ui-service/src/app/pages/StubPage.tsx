import type { ReactNode } from 'react';
import { PageHeader, Panel } from '../components/dashboard/primitives';

// Honest placeholder for pages whose backend data isn't available yet.
// Lists what the page will show and which data source will power it.
export function StubPage({
  title,
  subtitle,
  icon,
  planned,
  note,
}: {
  title: string;
  subtitle: string;
  icon: ReactNode;
  planned: string[];
  note?: string;
}) {
  return (
    <div>
      <PageHeader title={title} subtitle={subtitle} />
      <Panel className="p-10">
        <div className="flex flex-col items-center text-center max-w-lg mx-auto">
          <div className="text-gray-600 mb-4">{icon}</div>
          <p className="text-white font-medium">Coming in the next phase</p>
          {note && <p className="text-gray-400 text-sm mt-2">{note}</p>}
          <ul className="mt-6 space-y-2 text-left">
            {planned.map((p) => (
              <li key={p} className="flex items-start gap-2 text-sm text-gray-300">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                {p}
              </li>
            ))}
          </ul>
        </div>
      </Panel>
    </div>
  );
}
