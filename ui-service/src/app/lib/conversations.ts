// Conversation persistence for the AI Copilot (localStorage, per tenant).
// Backend conversation memory is Phase 2 on the server; this keeps history on
// the device meanwhile, with a shape that maps cleanly onto a future API.

export interface ChatTurn {
  role: 'user' | 'assistant';
  text: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  turns: ChatTurn[];
}

function key(tenantId: string) {
  return `devops-copilot.conversations.${tenantId}`;
}

export function loadConversations(tenantId: string): Conversation[] {
  try {
    const raw = localStorage.getItem(key(tenantId));
    const list = raw ? (JSON.parse(raw) as Conversation[]) : [];
    return list.sort((a, b) => b.updatedAt - a.updatedAt);
  } catch {
    return [];
  }
}

export function saveConversations(tenantId: string, conversations: Conversation[]): void {
  try {
    localStorage.setItem(key(tenantId), JSON.stringify(conversations));
  } catch {
    /* localStorage unavailable */
  }
}

export function newConversation(firstQuestion: string): Conversation {
  const now = Date.now();
  const title = firstQuestion.length > 40 ? firstQuestion.slice(0, 40) + '…' : firstQuestion;
  return {
    id: 'conv_' + Math.random().toString(36).slice(2, 10),
    title: title || 'New conversation',
    createdAt: now,
    updatedAt: now,
    turns: [],
  };
}

export type DayGroup = 'Today' | 'Yesterday' | 'Older';

export function groupByDay(conversations: Conversation[]): Record<DayGroup, Conversation[]> {
  const groups: Record<DayGroup, Conversation[]> = { Today: [], Yesterday: [], Older: [] };
  const startOfToday = new Date();
  startOfToday.setHours(0, 0, 0, 0);
  const startOfYesterday = startOfToday.getTime() - 86400000;

  for (const c of conversations) {
    if (c.updatedAt >= startOfToday.getTime()) groups.Today.push(c);
    else if (c.updatedAt >= startOfYesterday) groups.Yesterday.push(c);
    else groups.Older.push(c);
  }
  return groups;
}
