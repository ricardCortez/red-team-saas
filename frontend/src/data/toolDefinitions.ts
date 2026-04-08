import {
  Radar,
  Globe,
  Search,
  Key,
  Lock,
  ShieldAlert,
  FileSearch,
  Satellite,
  Binoculars,
  Info,
  Mail,
  Network,
  Database,
  Zap,
  Bug,
  Terminal,
  ArrowRight,
  type LucideIcon,
} from 'lucide-react';

export type ToolCategory =
  | 'All'
  | 'Scan'
  | 'Web'
  | 'Brute Force'
  | 'OSINT'
  | 'Exploitation'
  | 'Post-Exploitation'
  | 'Phishing';

export interface ToolParameter {
  name: string;
  label: string;
  type: 'text' | 'number' | 'select';
  required: boolean;
  placeholder: string;
  options?: string[]; // for select type
}

export interface ToolDefinition {
  id: string;
  name: string;
  category: Exclude<ToolCategory, 'All'>;
  icon: LucideIcon;
  description: string;
  parameters: ToolParameter[];
}

export const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    id: 'nmap',
    name: 'nmap',
    category: 'Scan',
    icon: Radar,
    description: 'Network exploration and security auditing. Discovers hosts, services, OS details, and open ports across a target network.',
    parameters: [
      { name: 'target', label: 'Target', type: 'text', required: true, placeholder: '192.168.1.0/24 or host.example.com' },
      { name: 'profile', label: 'Scan Profile', type: 'select', required: false, placeholder: 'quick', options: ['quick', 'standard', 'full', 'stealth'] },
    ],
  },
  {
    id: 'nikto',
    name: 'nikto',
    category: 'Web',
    icon: Globe,
    description: 'Web server scanner that detects dangerous files, outdated software, and configuration issues.',
    parameters: [
      { name: 'target', label: 'Target URL', type: 'text', required: true, placeholder: 'http://target.example.com' },
      { name: 'port', label: 'Port', type: 'number', required: false, placeholder: '80' },
      { name: 'ssl', label: 'Use SSL', type: 'select', required: false, placeholder: 'no', options: ['no', 'yes'] },
    ],
  },
  {
    id: 'gobuster',
    name: 'gobuster',
    category: 'Web',
    icon: Search,
    description: 'Directory/file and DNS brute-forcer. Finds hidden paths, subdomains, and virtual hosts.',
    parameters: [
      { name: 'target', label: 'Target URL', type: 'text', required: true, placeholder: 'http://target.example.com' },
      { name: 'wordlist', label: 'Wordlist', type: 'text', required: true, placeholder: '/usr/share/wordlists/dirb/common.txt' },
      { name: 'mode', label: 'Mode', type: 'select', required: false, placeholder: 'dir', options: ['dir', 'dns', 'vhost'] },
    ],
  },
  {
    id: 'hydra',
    name: 'hydra',
    category: 'Brute Force',
    icon: Key,
    description: 'Fast network login cracker. Supports dozens of protocols including SSH, FTP, HTTP, SMB, and more.',
    parameters: [
      { name: 'target', label: 'Target', type: 'text', required: true, placeholder: '192.168.1.100' },
      { name: 'service', label: 'Service', type: 'text', required: true, placeholder: 'ssh' },
      { name: 'username', label: 'Username', type: 'text', required: true, placeholder: 'admin' },
      { name: 'wordlist', label: 'Password Wordlist', type: 'text', required: true, placeholder: '/usr/share/wordlists/rockyou.txt' },
    ],
  },
  {
    id: 'john',
    name: 'john',
    category: 'Brute Force',
    icon: Lock,
    description: 'John the Ripper — offline password hash cracker supporting hundreds of hash formats.',
    parameters: [
      { name: 'hashfile', label: 'Hash File', type: 'text', required: true, placeholder: '/tmp/hashes.txt' },
      { name: 'format', label: 'Hash Format', type: 'text', required: false, placeholder: 'bcrypt' },
      { name: 'wordlist', label: 'Wordlist', type: 'text', required: false, placeholder: '/usr/share/wordlists/rockyou.txt' },
    ],
  },
  {
    id: 'medusa',
    name: 'medusa',
    category: 'Brute Force',
    icon: ShieldAlert,
    description: 'Speedy, massively parallel network login auditor. Similar to Hydra with different protocol support.',
    parameters: [
      { name: 'target', label: 'Target', type: 'text', required: true, placeholder: '192.168.1.100' },
      { name: 'username', label: 'Username', type: 'text', required: true, placeholder: 'admin' },
      { name: 'password', label: 'Password / Wordlist', type: 'text', required: true, placeholder: 'password123 or /path/to/wordlist.txt' },
      { name: 'module', label: 'Module', type: 'text', required: true, placeholder: 'ssh' },
    ],
  },
  {
    id: 'cewl',
    name: 'cewl',
    category: 'OSINT',
    icon: FileSearch,
    description: 'Custom Word List generator. Spiders a target website and generates wordlists from page content.',
    parameters: [
      { name: 'url', label: 'Target URL', type: 'text', required: true, placeholder: 'https://target.example.com' },
      { name: 'depth', label: 'Spider Depth', type: 'number', required: false, placeholder: '2' },
      { name: 'min_word_length', label: 'Min Word Length', type: 'number', required: false, placeholder: '6' },
    ],
  },
  {
    id: 'wpscan',
    name: 'wpscan',
    category: 'Web',
    icon: Search,
    description: 'WordPress vulnerability scanner. Enumerates users, plugins, themes, and known CVEs.',
    parameters: [
      { name: 'url', label: 'WordPress URL', type: 'text', required: true, placeholder: 'https://target-wordpress.com' },
      { name: 'enumerate', label: 'Enumerate', type: 'select', required: false, placeholder: 'users', options: ['users', 'plugins', 'themes', 'all'] },
    ],
  },
  {
    id: 'shodan',
    name: 'shodan',
    category: 'OSINT',
    icon: Satellite,
    description: 'Internet-connected device search engine. Find exposed services, default credentials, and IoT devices globally.',
    parameters: [
      { name: 'query', label: 'Search Query', type: 'text', required: true, placeholder: 'apache country:US port:8080' },
      { name: 'limit', label: 'Result Limit', type: 'number', required: false, placeholder: '50' },
    ],
  },
  {
    id: 'theharvester',
    name: 'theharvester',
    category: 'OSINT',
    icon: Binoculars,
    description: 'Gathers emails, subdomains, IPs, and URLs using multiple public data sources.',
    parameters: [
      { name: 'domain', label: 'Target Domain', type: 'text', required: true, placeholder: 'example.com' },
      { name: 'sources', label: 'Data Sources', type: 'text', required: false, placeholder: 'google,bing,linkedin' },
      { name: 'limit', label: 'Result Limit', type: 'number', required: false, placeholder: '100' },
    ],
  },
  {
    id: 'whois',
    name: 'whois',
    category: 'OSINT',
    icon: Info,
    description: 'Domain registration lookup. Reveals registrant, nameservers, registration dates, and contact details.',
    parameters: [
      { name: 'domain', label: 'Domain', type: 'text', required: true, placeholder: 'example.com' },
    ],
  },
  {
    id: 'hunter_io',
    name: 'hunter.io',
    category: 'OSINT',
    icon: Mail,
    description: 'Email finder and verifier. Discovers professional email addresses for a target domain.',
    parameters: [
      { name: 'domain', label: 'Domain', type: 'text', required: true, placeholder: 'example.com' },
      { name: 'api_key', label: 'API Key', type: 'text', required: true, placeholder: 'your-hunter-io-api-key' },
    ],
  },
  {
    id: 'passive_dns',
    name: 'passive_dns',
    category: 'OSINT',
    icon: Network,
    description: 'Passive DNS lookup using historical DNS records to discover subdomains and related infrastructure.',
    parameters: [
      { name: 'domain', label: 'Domain', type: 'text', required: true, placeholder: 'example.com' },
    ],
  },
  {
    id: 'sqlmap',
    name: 'sqlmap',
    category: 'Web',
    icon: Database,
    description: 'Automatic SQL injection detection and exploitation. Supports all major databases.',
    parameters: [
      { name: 'url', label: 'Target URL', type: 'text', required: true, placeholder: 'http://target.com/page?id=1' },
      { name: 'forms', label: 'Test Forms', type: 'select', required: false, placeholder: 'no', options: ['no', 'yes'] },
      { name: 'level', label: 'Level (1-5)', type: 'number', required: false, placeholder: '1' },
      { name: 'risk', label: 'Risk (1-3)', type: 'number', required: false, placeholder: '1' },
    ],
  },
  {
    id: 'metasploit',
    name: 'metasploit',
    category: 'Exploitation',
    icon: Zap,
    description: 'World\'s most used penetration testing framework. Exploit vulnerabilities, run payloads, and pivot.',
    parameters: [
      { name: 'module', label: 'Module', type: 'text', required: true, placeholder: 'exploit/multi/handler' },
      { name: 'rhosts', label: 'Target (RHOSTS)', type: 'text', required: true, placeholder: '192.168.1.100' },
      { name: 'payload', label: 'Payload', type: 'text', required: false, placeholder: 'windows/meterpreter/reverse_tcp' },
    ],
  },
  {
    id: 'burpsuite',
    name: 'burpsuite',
    category: 'Web',
    icon: Bug,
    description: 'Web application security testing platform. Intercept, scan, and attack HTTP/HTTPS traffic.',
    parameters: [
      { name: 'target', label: 'Target URL', type: 'text', required: true, placeholder: 'http://target.example.com' },
      { name: 'proxy_port', label: 'Proxy Port', type: 'number', required: false, placeholder: '8080' },
    ],
  },
  {
    id: 'gophish',
    name: 'gophish',
    category: 'Phishing',
    icon: Mail,
    description: 'Open-source phishing framework. Manage campaigns, track clicks, and capture credentials.',
    parameters: [
      { name: 'campaign_id', label: 'Campaign ID', type: 'number', required: true, placeholder: '1' },
    ],
  },
  {
    id: 'mimikatz',
    name: 'mimikatz',
    category: 'Post-Exploitation',
    icon: Key,
    description: 'Windows credential extraction tool. Dumps plaintext passwords, hashes, and Kerberos tickets from memory.',
    parameters: [
      { name: 'command', label: 'Command', type: 'text', required: true, placeholder: 'sekurlsa::logonpasswords' },
    ],
  },
  {
    id: 'empire',
    name: 'empire',
    category: 'Post-Exploitation',
    icon: Terminal,
    description: 'PowerShell and Python post-exploitation framework. Manage listeners, agents, and modules.',
    parameters: [
      { name: 'listener', label: 'Listener Name', type: 'text', required: true, placeholder: 'http' },
      { name: 'agent', label: 'Agent Name', type: 'text', required: false, placeholder: 'target-agent' },
    ],
  },
  {
    id: 'lateral_movement',
    name: 'lateral_movement',
    category: 'Post-Exploitation',
    icon: ArrowRight,
    description: 'Lateral movement techniques — pass-the-hash, WMI execution, PsExec, and more for pivoting through networks.',
    parameters: [
      { name: 'target', label: 'Target Host', type: 'text', required: true, placeholder: '192.168.1.50' },
      { name: 'technique', label: 'Technique', type: 'select', required: false, placeholder: 'pass-the-hash', options: ['pass-the-hash', 'wmi', 'psexec', 'smb'] },
    ],
  },
];

export const TOOL_CATEGORIES: ToolCategory[] = [
  'All',
  'Scan',
  'Web',
  'Brute Force',
  'OSINT',
  'Exploitation',
  'Post-Exploitation',
  'Phishing',
];

export const CATEGORY_COLORS: Record<Exclude<ToolCategory, 'All'>, string> = {
  'Scan': 'text-[var(--color-neon-blue)] border-[var(--color-neon-blue)]',
  'Web': 'text-[var(--color-neon-green)] border-[var(--color-neon-green)]',
  'Brute Force': 'text-[var(--color-neon-red)] border-[var(--color-neon-red)]',
  'OSINT': 'text-yellow-400 border-yellow-400',
  'Exploitation': 'text-orange-400 border-orange-400',
  'Post-Exploitation': 'text-purple-400 border-purple-400',
  'Phishing': 'text-pink-400 border-pink-400',
};
