import { useState, useEffect } from 'react';
import { X, Play, ExternalLink } from 'lucide-react';
import type { ToolDefinition } from '../../data/toolDefinitions';
import api from '../../services/api';

interface Project {
  id: number;
  name: string;
}

interface ToolExecuteModalProps {
  tool: ToolDefinition | null;
  onClose: () => void;
}

export function ToolExecuteModal({ tool, onClose }: ToolExecuteModalProps) {
  const [params, setParams] = useState<Record<string, string>>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [executionId, setExecutionId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!tool) return;
    setParams({});
    setExecutionId(null);
    setError(null);
    api.get('/projects/')
      .then((r) => {
        const list: Project[] = Array.isArray(r.data) ? r.data : (r.data.items ?? []);
        setProjects(list);
        if (list.length > 0) setSelectedProject(String(list[0].id));
      })
      .catch(() => {});
  }, [tool]);

  if (!tool) return null;

  const Icon = tool.icon;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject) { setError('Select a project first.'); return; }
    setLoading(true);
    setError(null);
    try {
      const res = await api.post('/executions/', {
        tool_name: tool.id,
        parameters: params,
        project_id: Number(selectedProject),
      });
      setExecutionId(res.data.id);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? 'Execution failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-lg bg-[#0a0a0a] border border-white/10 rounded-lg shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <Icon className="w-5 h-5 text-[var(--color-neon-green)]" />
            <span className="font-mono text-sm font-bold text-[var(--color-neon-green)]">{tool.name}</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4">
          <p className="text-xs text-gray-400 mb-4">{tool.description}</p>

          {executionId ? (
            <div className="text-center py-6">
              <p className="text-[var(--color-neon-green)] font-mono text-sm mb-2">
                Execution started — ID #{executionId}
              </p>
              <a
                href="/scans"
                className="inline-flex items-center gap-1.5 text-xs text-[var(--color-neon-blue)] hover:underline"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                View results in Scans
              </a>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-3">
              {/* Project selector */}
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Project <span className="text-[var(--color-neon-red)]">*</span>
                </label>
                <select
                  value={selectedProject}
                  onChange={(e) => setSelectedProject(e.target.value)}
                  className="w-full bg-black/60 border border-white/20 rounded px-3 py-2 text-sm text-white focus:border-[var(--color-neon-green)] focus:outline-none"
                  required
                >
                  <option value="">-- Select project --</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              {/* Dynamic parameters */}
              {tool.parameters.map((param) => (
                <div key={param.name}>
                  <label className="block text-xs text-gray-400 mb-1">
                    <span className="font-mono text-[var(--color-neon-blue)]">{param.name}</span>
                    {' '}
                    <span className="text-gray-500">({param.label})</span>
                    {param.required && <span className="text-[var(--color-neon-red)] ml-1">*</span>}
                  </label>
                  {param.type === 'select' ? (
                    <select
                      value={params[param.name] ?? ''}
                      onChange={(e) => setParams((p) => ({ ...p, [param.name]: e.target.value }))}
                      className="w-full bg-black/60 border border-white/20 rounded px-3 py-2 text-sm text-white focus:border-[var(--color-neon-green)] focus:outline-none"
                    >
                      <option value="">{param.placeholder}</option>
                      {param.options?.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={param.type}
                      value={params[param.name] ?? ''}
                      onChange={(e) => setParams((p) => ({ ...p, [param.name]: e.target.value }))}
                      placeholder={param.placeholder}
                      required={param.required}
                      className="w-full bg-black/60 border border-white/20 rounded px-3 py-2 text-sm text-white placeholder-gray-600 focus:border-[var(--color-neon-green)] focus:outline-none"
                    />
                  )}
                </div>
              ))}

              {error && (
                <p className="text-xs text-[var(--color-neon-red)]">{error}</p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2 border border-[var(--color-neon-green)] text-[var(--color-neon-green)] font-mono text-sm rounded hover:bg-[var(--color-neon-green)] hover:text-black transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-4 h-4" />
                {loading ? 'Launching...' : 'Run'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
