export interface Project {
  id: string;
  name: string;
  path: string;
  type: 'node' | 'python' | 'rust' | 'docker' | 'generic';
  tags: string[];
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

export interface HomepageService {
  name: string;
  links: string[];
  icons: string[];
  metrics: { label: string; value: string }[];
  snippet: string;
}

export interface ScrutinyDrive {
  device: string;
  bus_model: string;
  last_updated: string;
  status: string;
  temp: string;
  capacity: string;
  powered_on: string;
}

export interface HostServiceStatus {
  name: string;
  state: string;
  details: Record<string, unknown>;
}

export interface HostStatusResponse {
  timestamp: string;
  services: HostServiceStatus[];
}

export interface HardwareMetricSnapshot {
  timestamp?: string;
  metrics?: Record<string, unknown>;
  cpu?: { temp_c?: number; load_pct?: number; clock_mhz?: number };
  gpu?: { temp_c?: number; load_pct?: number; clock_mhz?: number };
  ram?: { used_gb?: number; load_pct?: number };
  board?: { vrm_temp_c?: number; mobo_temp_c?: number };
  fans?: { id?: string; name?: string; rpm?: number }[];
  drives?: {
    id?: string;
    name?: string;
    temp_c?: number;
    used_pct?: number;
    read_rate_mbps?: number;
    write_rate_mbps?: number;
  }[];
  network?: Record<
    string,
    {
      upload_rate_mbps?: number;
      download_rate_mbps?: number;
      data_uploaded_gb?: number;
      data_downloaded_gb?: number;
    }
  >;
}

export interface HardwareHistoryResponse {
  latest?: HardwareMetricSnapshot;
  history?: HardwareMetricSnapshot[];
}

export interface HostLogsResponse {
  service: string;
  lines: string[];
  raw?: string;
}

export interface Platform {
  id: string;
  name: string;
  url: string;
}
