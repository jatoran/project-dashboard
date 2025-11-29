export interface Project {
  id: string;
  name: string;
  path: string;
  type: 'node' | 'python' | 'rust' | 'docker' | 'generic';
  tags: string[];
  git_status?: string;
  docs: { name: string; path: string }[];
}
