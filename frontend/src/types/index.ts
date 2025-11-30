export interface Project {
  id: string;
  name: string;
  path: string;
  type: 'node' | 'python' | 'rust' | 'docker' | 'generic';
  tags: string[];
  git_status?: string;
  docs: { name: string; path: string; type?: 'openapi' | 'swagger' | 'file' | 'link' | 'markdown' }[];
  vscode_workspace_file?: string;
  frontend_url?: string;
}

export interface HomepageService {
  name: string;
  links: string[];
  icons: string[];
  metrics: { label: string; value: string }[];
  snippet: string;
}
