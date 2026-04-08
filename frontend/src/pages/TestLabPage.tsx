import { useState, useEffect } from 'react';
import { Play, Mail, FileText, ExternalLink, Clock, AlertCircle } from 'lucide-react';
import { ServiceHealthCard } from '../components/TestLab/ServiceHealthCard';

interface Execution {
  id: number;
  tool_name: string;
  status: string;
  created_at: string;
}

interface Campaign {
  id: number;
  name: string;
  status: string;
  created_date: string;
}

interface Stats {
  findings: number;
  scans: number;
  projects: number;
  targets: number;
}

const API_BASE = '/api/v1';

const SERVICES = [
  { name: 'API', url: `${window.location.origin}/api/v1/`, description: 'FastAPI backend' },
  { name: 'GoPhish', url: 'https://localhost:3333', description: 'Phishing admin UI' },
  { name: 'Grafana', url: 'http://localhost:3000', description: 'Monitoring dashboards' },
  { name: 'Prometheus', url: 'http://localhost:9090', description: 'Metrics collector' },
  { name: 'Flower', url: 'http://localhost:5555', description: 'Celery task monitor' },
];

const QUICK_LINKS = [
  { label: 'Grafana', url: 'http://localhost:3000', icon: ExternalLink },
  { label: 'Prometheus', url: 'http://localhost:9090', icon: ExternalLink },
  { label: 'Flower', url: 'http://localhost:5555', icon: ExternalLink },
  { label: 'Swagger Docs', url: '/api/docs', icon: ExternalLink },
];

function getAuthHeaders() {
  const token = localStorage.getItem('token') ?? '';
  return { Authorization: `Bearer ${token}` };
}

function statusColor(status: string) {
  switch (status?.toLowerCase()) {
    case 'completed': case 'success': case 'active': return 'text-[var(--color-neon-green)]';
    case 'running': case 'in_progress': return 'text-[var(--color-neon-blue)]';
    case 'failed': case 'error': return 'text-[var(--color-neon-red)]';
    default: return 'text-gray-400';
  }
}

export default function TestLabPage() {
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [stats, setStats] = useState<Stats>({ findings: 0, scans: 0, projects: 0, targets: 0 });
  const [scanTarget, setScanTarget] = useState('');
  const [scanLoading, setScanLoading] = useState(false);
  const [scanResult, setScanResult] = useState<{ id: number } | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportResult, setReportResult] = useState<string | null>(null);

  useEffect(() => {
    const headers = getAuthHeaders();

    // Recent executions
    fetch(`${API_BASE}/executions/?limit=10`, { headers })
      .then((r) => r.json())
      .then((data) => setExecutions(Array.isArray(data) ? data : data.items ?? []))
      .catch(() => {});

    // Recent campaigns
    fetch(`${API_BASE}/phishing/campaigns/?limit=5`, { headers })
      .then((r) => r.json())
      .then((data) => setCampaigns(Array.isArray(data) ? data : data.items ?? []))
      .catch(() => {});

    // Stats
    Promise.all([
      fetch(`${API_BASE}/findings/`, { headers }).then((r) => r.json()).catch(() => []),
      fetch(`${API_BASE}/executions/`, { headers }).then((r) => r.json()).catch(() => []),
      fetch(`${API_BASE}/projects/`, { headers }).then((r) => r.json()).catch(() => []),
      fetch(`${API_BASE}/targets/`, { headers }).then((r) => r.json()).catch(() => []),
    ]).then(([findings, scans, projects, targets]) => {
      const count = (d: unknown) => {
        if (Array.isArray(d)) return d.length;
        if (d && typeof d === 'object' && 'total' in d) return (d as { total: number }).total;
        return 0;
      };
      setStats({
        findings: count(findings),
        scans: count(scans),
        projects: count(projects),
        targets: count(targets),
      });
    });
  }, []);

  const handleQuickScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scanTarget) return;
    setScanLoading(true);
    setScanResult(null);
    try {
      // Get first project
      const projects = await fetch(`${API_BASE}/projects/`, { headers: getAuthHeaders() })
        .then((r) => r.json());
      const projectList = Array.isArray(projects) ? projects : projects.items ?? [];
      if (projectList.length === 0) { alert('No projects available. Create a project first.'); return; }
      const res = await fetch(`${API_BASE}/executions/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ tool_name: 'nmap', parameters: { target: scanTarget, profile: 'quick' }, project_id: projectList[0].id }),
      });
      const data = await res.json();
      if (res.ok) setScanResult({ id: data.id });
    } catch {
      /* ignore */
    } finally {
      setScanLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setReportLoading(true);
    setReportResult(null);
    try {
      const projects = await fetch(`${API_BASE}/projects/`, { headers: getAuthHeaders() }).then((r) => r.json());
      const projectList = Array.isArray(projects) ? projects : projects.items ?? [];
      if (projectList.length === 0) { setReportResult('No projects found.'); return; }
      const res = await fetch(`${API_BASE}/reports/generate/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ project_id: projectList[0].id }),
      });
      if (res.ok) {
        setReportResult(`Report generated for project "${projectList[0].name}"`);
      } else {
        setReportResult('Report generation failed or not supported.');
      }
    } catch {
      setReportResult('Error generating report.');
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-mono font-bold text-[var(--color-neon-green)]">Test Lab</h1>
        <p className="text-xs text-gray-400 mt-1">Validate system features and monitor service health</p>
      </div>

      {/* System Health */}
      <section>
        <h2 className="text-sm font-mono text-gray-300 mb-3 uppercase tracking-wider">System Health</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {SERVICES.map((svc) => (
            <ServiceHealthCard key={svc.name} name={svc.name} url={svc.url} description={svc.description} />
          ))}
        </div>
      </section>

      {/* Quick Actions */}
      <section>
        <h2 className="text-sm font-mono text-gray-300 mb-3 uppercase tracking-wider">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Quick Scan */}
          <div className="border border-white/10 rounded-lg bg-black/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Play className="w-4 h-4 text-[var(--color-neon-green)]" />
              <span className="font-mono text-sm text-white">Quick Scan</span>
            </div>
            <form onSubmit={handleQuickScan} className="space-y-2">
              <input
                type="text"
                value={scanTarget}
                onChange={(e) => setScanTarget(e.target.value)}
                placeholder="192.168.1.1 or example.com"
                className="w-full bg-black/60 border border-white/20 rounded px-3 py-1.5 text-xs text-white placeholder-gray-600 focus:border-[var(--color-neon-green)] focus:outline-none"
              />
              <button
                type="submit"
                disabled={scanLoading || !scanTarget}
                className="w-full py-1.5 text-xs font-mono border border-[var(--color-neon-green)] text-[var(--color-neon-green)] rounded hover:bg-[var(--color-neon-green)] hover:text-black transition-all disabled:opacity-50"
              >
                {scanLoading ? 'Launching...' : 'Launch nmap -Quick'}
              </button>
              {scanResult && (
                <p className="text-xs text-[var(--color-neon-green)]">
                  Scan #{scanResult.id} started · <a href="/scans" className="underline">View results</a>
                </p>
              )}
            </form>
          </div>

          {/* Quick Phishing */}
          <div className="border border-white/10 rounded-lg bg-black/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <Mail className="w-4 h-4 text-[var(--color-neon-green)]" />
              <span className="font-mono text-sm text-white">Quick Phishing</span>
            </div>
            <p className="text-xs text-gray-400 mb-3">Create a draft campaign using the base GoPhish templates.</p>
            <a
              href="/phishing"
              className="block w-full text-center py-1.5 text-xs font-mono border border-[var(--color-neon-green)] text-[var(--color-neon-green)] rounded hover:bg-[var(--color-neon-green)] hover:text-black transition-all"
            >
              Open Phishing Console
            </a>
          </div>

          {/* Generate Report */}
          <div className="border border-white/10 rounded-lg bg-black/40 p-4">
            <div className="flex items-center gap-2 mb-3">
              <FileText className="w-4 h-4 text-[var(--color-neon-green)]" />
              <span className="font-mono text-sm text-white">Generate Report</span>
            </div>
            <p className="text-xs text-gray-400 mb-3">Trigger report generation for the first available project.</p>
            <button
              onClick={handleGenerateReport}
              disabled={reportLoading}
              className="w-full py-1.5 text-xs font-mono border border-[var(--color-neon-green)] text-[var(--color-neon-green)] rounded hover:bg-[var(--color-neon-green)] hover:text-black transition-all disabled:opacity-50"
            >
              {reportLoading ? 'Generating...' : 'Generate Report'}
            </button>
            {reportResult && (
              <p className="text-xs text-gray-400 mt-2">{reportResult}</p>
            )}
          </div>
        </div>
      </section>

      {/* Quick Links */}
      <section>
        <h2 className="text-sm font-mono text-gray-300 mb-3 uppercase tracking-wider">Quick Links</h2>
        <div className="flex flex-wrap gap-3">
          {QUICK_LINKS.map((link) => {
            const Icon = link.icon;
            return (
              <a
                key={link.label}
                href={link.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-4 py-2 border border-white/20 rounded text-sm text-gray-300 hover:border-[var(--color-neon-green)] hover:text-[var(--color-neon-green)] transition-all font-mono"
              >
                <Icon className="w-3.5 h-3.5" />
                {link.label}
              </a>
            );
          })}
        </div>
      </section>

      {/* System Stats */}
      <section>
        <h2 className="text-sm font-mono text-gray-300 mb-3 uppercase tracking-wider">System Stats</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: 'Findings', value: stats.findings },
            { label: 'Scans', value: stats.scans },
            { label: 'Projects', value: stats.projects },
            { label: 'Targets', value: stats.targets },
          ].map((stat) => (
            <div key={stat.label} className="border border-white/10 rounded-lg bg-black/40 p-4 text-center">
              <div className="text-2xl font-mono font-bold text-[var(--color-neon-green)]">{stat.value}</div>
              <div className="text-xs text-gray-400 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Recent Activity Feed */}
      <section>
        <h2 className="text-sm font-mono text-gray-300 mb-3 uppercase tracking-wider">Recent Activity</h2>
        <div className="space-y-2">
          {executions.length === 0 && campaigns.length === 0 ? (
            <div className="flex items-center gap-2 text-gray-500 text-sm py-4 justify-center">
              <AlertCircle className="w-4 h-4" />
              No recent activity
            </div>
          ) : (
            <>
              {executions.slice(0, 10).map((exec) => (
                <div key={`exec-${exec.id}`} className="flex items-center justify-between p-3 border border-white/10 rounded bg-black/40 text-xs">
                  <div className="flex items-center gap-2">
                    <Play className="w-3.5 h-3.5 text-[var(--color-neon-blue)]" />
                    <span className="font-mono text-gray-300">Scan #{exec.id}</span>
                    <span className="text-gray-500">·</span>
                    <span className="font-mono text-white">{exec.tool_name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`font-mono ${statusColor(exec.status)}`}>{exec.status}</span>
                    <span className="text-gray-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(exec.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
              {campaigns.slice(0, 5).map((camp) => (
                <div key={`camp-${camp.id}`} className="flex items-center justify-between p-3 border border-white/10 rounded bg-black/40 text-xs">
                  <div className="flex items-center gap-2">
                    <Mail className="w-3.5 h-3.5 text-pink-400" />
                    <span className="font-mono text-gray-300">Campaign #{camp.id}</span>
                    <span className="text-gray-500">·</span>
                    <span className="font-mono text-white">{camp.name}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`font-mono ${statusColor(camp.status)}`}>{camp.status}</span>
                    <span className="text-gray-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {new Date(camp.created_date).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </section>
    </div>
  );
}
