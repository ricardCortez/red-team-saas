import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';
import { TOOL_DEFINITIONS, TOOL_CATEGORIES } from '../data/toolDefinitions';
import type { ToolDefinition, ToolCategory } from '../data/toolDefinitions';
import { ToolCard } from '../components/Tools/ToolCard';
import { ToolExecuteModal } from '../components/Tools/ToolExecuteModal';

// Tools that are actually installed/available on the system
const AVAILABLE_TOOLS = new Set([
  'nmap', 'nikto', 'gobuster', 'hydra', 'john', 'medusa', 'cewl',
  'wpscan', 'theharvester', 'whois', 'sqlmap', 'gophish',
]);

export default function ToolsPage() {
  const [activeCategory, setActiveCategory] = useState<ToolCategory>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);

  const filteredTools = useMemo(() => {
    return TOOL_DEFINITIONS.filter((tool) => {
      const matchesCategory = activeCategory === 'All' || tool.category === activeCategory;
      const matchesSearch =
        searchQuery === '' ||
        tool.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tool.category.toLowerCase().includes(searchQuery.toLowerCase());
      return matchesCategory && matchesSearch;
    });
  }, [activeCategory, searchQuery]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-mono font-bold text-[var(--color-neon-green)]">
            Tools Catalog
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            {TOOL_DEFINITIONS.length} tools available ·{' '}
            {TOOL_DEFINITIONS.filter((t) => AVAILABLE_TOOLS.has(t.id)).length} installed
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tools..."
            className="pl-9 pr-4 py-2 bg-black/60 border border-white/20 rounded text-sm text-white placeholder-gray-600 focus:border-[var(--color-neon-green)] focus:outline-none w-56"
          />
        </div>
      </div>

      {/* Category Tabs */}
      <div className="flex flex-wrap gap-2">
        {TOOL_CATEGORIES.map((cat) => {
          const count = cat === 'All'
            ? TOOL_DEFINITIONS.length
            : TOOL_DEFINITIONS.filter((t) => t.category === cat).length;
          return (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`px-3 py-1.5 text-xs font-mono rounded border transition-all duration-150 ${
                activeCategory === cat
                  ? 'border-[var(--color-neon-green)] text-[var(--color-neon-green)] bg-[var(--color-neon-green)]/10'
                  : 'border-white/20 text-gray-400 hover:border-white/40 hover:text-white'
              }`}
            >
              {cat} <span className="opacity-60">({count})</span>
            </button>
          );
        })}
      </div>

      {/* Tool Grid */}
      {filteredTools.length === 0 ? (
        <div className="text-center py-16 text-gray-500 font-mono text-sm">
          No tools match "{searchQuery}"
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredTools.map((tool) => (
            <ToolCard
              key={tool.id}
              tool={tool}
              isAvailable={AVAILABLE_TOOLS.has(tool.id)}
              onExecute={setSelectedTool}
            />
          ))}
        </div>
      )}

      {/* Execute Modal */}
      <ToolExecuteModal
        tool={selectedTool}
        onClose={() => setSelectedTool(null)}
      />
    </div>
  );
}
