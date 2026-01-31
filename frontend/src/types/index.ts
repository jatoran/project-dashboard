export interface Project {
  id: string;
  name: string;
  path: string;
  type: 'node' | 'python' | 'rust' | 'docker' | 'generic' | 'static-web' | 'java' | 'go' | 'ruby' | 'php';
  tags: string[];
  description?: string;
  git_status?: string;
  docs: { name: string; path: string; type?: 'openapi' | 'swagger' | 'file' | 'link' | 'markdown' }[];
  custom_links?: { name: string; url: string }[];
  custom_docs?: { name: string; path: string }[];
  vscode_workspace_file?: string;
  frontend_url?: string;
  backend_port?: string | null;
  frontend_port_override?: string | null;
  backend_port_override?: string | null;
  position?: number | null;
}

export type SortMode = 'custom' | 'name' | 'created' | 'modified';

export interface Platform {
  id: string;
  name: string;
  url: string;
}
