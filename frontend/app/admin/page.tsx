'use client';

import { useState, useEffect, useCallback } from 'react';
import { ApiService, AdminMetrics, AuditLogEntry, AuthUserPayload } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { useLogout } from '@/components/AuthProvider';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { RefreshCw, LogOut, ArrowLeft, ShieldAlert, Plus, Ban } from 'lucide-react';

/* ─── metric card ────────────────────────────────────────────────────────── */
function MetricCard({ title, value, sub, colorClass }: { title: string; value: string | number; sub?: string; colorClass: string }) {
  return (
    <div className={`glass-panel bg-white/50 dark:bg-black/20 p-6 relative overflow-hidden rounded-2xl border shadow-sm hover:shadow-md transition-shadow duration-200 ${colorClass}`}>
      <div className="absolute -top-6 -right-6 w-24 h-24 rounded-full bg-current opacity-10" />
      <p className="text-3xl font-bold text-foreground mb-1.5">{value}</p>
      <p className="text-sm font-medium text-muted-foreground">{title}</p>
      {sub && <p className="text-xs text-muted-foreground/70 mt-1.5">{sub}</p>}
    </div>
  );
}

/* ─── role badge ─────────────────────────────────────────────────────────── */
function RoleBadge({ role }: { role: string }) {
  const map: Record<string, string> = {
    admin:    'bg-violet-100 text-violet-700 border-violet-200 dark:bg-violet-900/30 dark:text-violet-300 dark:border-violet-800',
    hr:       'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
    employee: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/30 dark:text-slate-300 dark:border-slate-700',
  };
  const classes = map[role] ?? map.employee;
  return (
    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border tracking-wide uppercase ${classes}`}>
      {role}
    </span>
  );
}

/* ─── main page ──────────────────────────────────────────────────────────── */
export default function AdminPage() {
  const { user } = useAuthStore();
  const logout = useLogout();
  const router = useRouter();

  useEffect(() => {
    if (user && user.role !== 'admin' && user.role !== 'hr') {
      router.replace('/');
    }
  }, [user, router]);

  const [tab, setTab] = useState<'overview' | 'logs' | 'users'>('overview');
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [users, setUsers] = useState<AuthUserPayload[]>([]);
  const [blockedOnly, setBlockedOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newUser, setNewUser] = useState({ email: '', username: '', password: '', role: 'employee', full_name: '' });
  const [createError, setCreateError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setMetrics(await ApiService.getAdminMetrics());
      if (tab === 'logs') setLogs(await ApiService.getAuditLogs(blockedOnly, 100));
      if (tab === 'users') setUsers(await ApiService.getUsers());
    } catch { /* ignore */ } finally { setLoading(false); }
  }, [tab, blockedOnly]);

  useEffect(() => { refresh(); }, [refresh]);

  async function handleRoleChange(userId: string, role: string) {
    try { const u = await ApiService.updateUser(userId, { role }); setUsers(us => us.map(x => x.id === userId ? u : x)); }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed'); }
  }

  async function handleDeactivate(userId: string) {
    if (!confirm('Deactivate this user?')) return;
    try { await ApiService.deactivateUser(userId); setUsers(us => us.map(x => x.id === userId ? { ...x, is_active: false } : x)); }
    catch (e) { alert(e instanceof Error ? e.message : 'Failed'); }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setCreateError('');
    try {
      const created = await ApiService.createAdminUser(newUser);
      if (!created || typeof created !== 'object' || !created.id) {
        throw new Error("Invalid response from server");
      }
      setUsers(us => [created, ...us]);
      setShowCreate(false);
      setNewUser({ email: '', username: '', password: '', role: 'employee', full_name: '' });
    } catch (e) { setCreateError(e instanceof Error ? e.message : 'Failed to create user'); }
  }

  const tabs = [
    { id: 'overview' as const, label: 'Overview' },
    { id: 'logs'     as const, label: 'Audit Logs' },
    { id: 'users'    as const, label: 'Users' },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Header */}
      <header className="sticky top-0 z-50 glass-panel border-b px-6 md:px-8 h-16 flex items-center justify-between shadow-sm bg-background/80">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground text-sm font-medium transition-colors">
            <ArrowLeft className="h-4 w-4" /> Back
          </Link>
          <span className="text-border">|</span>
          <div className="flex items-center gap-2.5">
            <ShieldAlert className="h-5 w-5 text-primary" />
            <span className="font-bold text-lg text-foreground">Admin Dashboard</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <span className="text-sm flex items-center gap-2 text-muted-foreground">
              <span>{user.username}</span>
              <RoleBadge role={user.role} />
            </span>
          )}
          <Button variant="outline" size="sm" onClick={refresh} disabled={loading} className="gap-2 h-8">
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button variant="ghost" size="sm" onClick={logout} className="gap-2 h-8 text-muted-foreground hover:text-destructive">
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Tab nav */}
        <div className="inline-flex glass-panel p-1.5 rounded-2xl border mb-8 bg-white/50 dark:bg-black/20">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-6 py-2.5 text-sm font-medium rounded-xl transition-all ${
                tab === t.id
                  ? 'bg-primary text-primary-foreground shadow-md'
                  : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ─── OVERVIEW ─── */}
        {tab === 'overview' && metrics && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard title="Total Queries" value={metrics.queries.total} sub={`${metrics.queries.last_24h} in last 24h`} colorClass="text-blue-500" />
              <MetricCard title="Block Rate" value={`${metrics.queries.block_rate_pct}%`} sub={`${metrics.queries.blocked_total} blocked`} colorClass="text-destructive" />
              <MetricCard title="Avg Latency" value={`${metrics.performance.avg_latency_ms}ms`} colorClass="text-amber-500" />
              <MetricCard title="Avg Confidence" value={`${metrics.performance.avg_confidence}%`} colorClass="text-emerald-500" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricCard title="Total Users" value={metrics.users.total} sub={`${metrics.users.active} active`} colorClass="text-purple-500" />
              <MetricCard title="Thumbs Up" value={metrics.feedback.thumbs_up} colorClass="text-emerald-500" />
              <MetricCard title="Satisfaction" value={`${metrics.feedback.satisfaction_pct}%`} sub={`${metrics.feedback.thumbs_down} thumbs down`} colorClass="text-pink-500" />
            </div>
          </div>
        )}

        {/* ─── AUDIT LOGS ─── */}
        {tab === 'logs' && (
          <div className="space-y-4">
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={blockedOnly}
                  onChange={e => setBlockedOnly(e.target.checked)}
                  className="rounded border-input text-primary focus:ring-primary h-4 w-4"
                />
                Blocked only
              </label>
              <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded-full">{logs.length} entries</span>
            </div>
            
            <div className="glass-panel bg-white/60 dark:bg-black/20 border rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-white/40 dark:bg-black/40 text-muted-foreground">
                    <tr>
                      {['Time', 'Query', 'Status', 'Confidence', 'Latency', 'Sources'].map(h => (
                        <th key={h} className="px-5 py-3.5 font-semibold tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {logs.map((log) => (
                      <tr key={log.id} className={`hover:bg-white/70 dark:hover:bg-white/5 transition-colors ${log.blocked ? 'bg-destructive/5' : ''}`}>
                        <td className="px-4 py-3 text-muted-foreground whitespace-nowrap text-xs">{new Date(log.created_at).toLocaleString()}</td>
                        <td className="px-4 py-3 text-foreground max-w-[280px] truncate" title={log.query}>{log.query}</td>
                        <td className="px-4 py-3">
                          {log.blocked ? (
                            <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-destructive/10 text-destructive border border-destructive/20 font-medium">
                              <Ban className="h-3 w-3" /> Blocked
                            </span>
                          ) : (
                            <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-medium">
                              OK
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{log.confidence != null ? `${log.confidence}%` : '—'}</td>
                        <td className="px-4 py-3 text-muted-foreground">{log.latency_ms != null ? `${log.latency_ms}ms` : '—'}</td>
                        <td className="px-4 py-3 text-muted-foreground">{log.sources_count}</td>
                      </tr>
                    ))}
                    {logs.length === 0 && (
                      <tr><td colSpan={6} className="px-6 py-12 text-center text-muted-foreground">No audit logs found</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ─── USERS ─── */}
        {tab === 'users' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground bg-muted/50 px-3 py-1 rounded-full">{users.length} users</span>
              <Button onClick={() => setShowCreate(v => !v)} className="gap-2">
                <Plus className="h-4 w-4" /> New User
              </Button>
            </div>

            {/* Create user form */}
            {showCreate && (
              <form onSubmit={handleCreate} className="glass-panel bg-white/70 dark:bg-black/30 border p-6 rounded-xl shadow-sm mb-6">
                <h3 className="text-lg font-semibold mb-4 text-foreground">Create New User</h3>
                {createError && <p className="text-sm text-destructive mb-4 bg-destructive/10 px-3 py-2 rounded-md">{createError}</p>}
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  {[
                    { field: 'full_name', label: 'Full Name',  type: 'text'     },
                    { field: 'email',     label: 'Email',       type: 'email'    },
                    { field: 'username',  label: 'Username',    type: 'text'     },
                    { field: 'password',  label: 'Password',    type: 'password' },
                  ].map(({ field, label, type }) => (
                    <div key={field}>
                      <label className="block text-xs font-medium text-muted-foreground mb-1">{label}</label>
                      <Input
                        type={type}
                        required={field !== 'full_name'}
                        value={newUser[field as keyof typeof newUser]}
                        onChange={e => setNewUser(u => ({ ...(u || { email: '', username: '', password: '', role: 'employee', full_name: '' }), [field]: e.target.value }))}
                        className="bg-background/50"
                      />
                    </div>
                  ))}
                </div>
                
                <div className="mb-6">
                  <label className="block text-xs font-medium text-muted-foreground mb-1">Role</label>
                  <select
                    value={newUser?.role || 'employee'}
                    onChange={e => setNewUser(u => ({ ...(u || { email: '', username: '', password: '', role: 'employee', full_name: '' }), role: e.target.value }))}
                    className="flex h-9 w-full sm:w-64 items-center justify-between rounded-md border border-input bg-background/50 px-3 py-2 text-sm shadow-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="employee">Employee</option>
                    <option value="hr">HR</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                
                <div className="flex gap-3">
                  <Button type="submit">Create User</Button>
                  <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
                </div>
              </form>
            )}

            <div className="glass-panel bg-white/60 dark:bg-black/20 border rounded-xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-white/40 dark:bg-black/40 text-muted-foreground">
                    <tr>
                      {['User', 'Email', 'Role', 'Status', 'Joined', 'Actions'].map(h => (
                        <th key={h} className="px-4 py-3 font-semibold tracking-wider">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {users.map((u) => {
                      if (!u) return null;
                      return (
                      <tr key={u.id || Math.random().toString()} className="hover:bg-white/70 dark:hover:bg-white/5 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white font-bold text-xs bg-primary shadow-sm">
                              {((u.full_name || u.username) && typeof (u.full_name || u.username) === 'string' ? (u.full_name || u.username)[0].toUpperCase() : '?')}
                            </div>
                            <span className="font-medium text-foreground">{u.full_name || u.username || 'Unknown'}</span>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground">{u.email}</td>
                        <td className="px-4 py-3">
                          <select
                            value={u.role || 'employee'}
                            onChange={e => handleRoleChange(u.id, e.target.value)}
                            className="bg-background/80 border border-input text-foreground rounded-md px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-primary shadow-sm"
                          >
                            <option value="employee">Employee</option>
                            <option value="hr">HR</option>
                            <option value="admin">Admin</option>
                          </select>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center text-xs px-2 py-0.5 rounded-full border font-medium ${
                            u.is_active 
                              ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 dark:text-emerald-400' 
                              : 'bg-muted text-muted-foreground border-border'
                          }`}>
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-muted-foreground text-xs">{u.created_at ? new Date(u.created_at).toLocaleDateString() : ''}</td>
                        <td className="px-4 py-3">
                          {u.is_active && u.id && (
                            <Button variant="ghost" size="sm" onClick={() => handleDeactivate(u.id)} className="h-8 text-muted-foreground hover:text-destructive hover:bg-destructive/10">
                              <Ban className="h-3.5 w-3.5 mr-1.5" /> Deactivate
                            </Button>
                          )}
                        </td>
                      </tr>
                    )})}
                    {users.length === 0 && (
                      <tr><td colSpan={6} className="px-6 py-12 text-center text-muted-foreground">No users found</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
