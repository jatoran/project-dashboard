# Technical Documentation

## Architecture Overview
The Project Dashboard is a Next.js application designed to bridge the gap between a WSL development environment and the Windows GUI workflow. It acts as a local server that indexes files and spawns system processes.

## File System & Interop
Since the application runs in WSL but manages Windows-centric workflows (VS Code, Explorer, Windows Terminal), it relies heavily on WSL Interoperability.

### Path Translation
The system must handle path conversions between POSIX (WSL) and Windows formats:
- **WSL:** `/mnt/d/projects/my-app`
- **Windows:** `D:\projects\my-app` (or network path `\\wsl.localhost\Ubuntu\home…`)

### Launch Strategies
1.  **VS Code:** `code /mnt/d/projects/my-app` (WSL `code` command handles the remote context automatically).
2.  **Explorer:** `explorer.exe "D:\projects\my-app"` (Requires explicit translation).
3.  **Terminal:** `cmd.exe /c start wt.exe ...`

## Data Model
**Project Entry:**
```typescript
interface Project {
  id: string;
  name: string;
  path: string; // WSL Path
  tags: string[];
  metadata: {
    type: 'node' | 'python' | 'rust' | 'generic';
    hasGit: boolean;
    docs: DocLink[];
  }
}
```

