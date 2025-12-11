// 解析文件 URL，支持相对路径与完整 URL
export function resolveFileUrl(path: string | undefined): string {
  if (!path) return "";
  // 如果已经是完整URL，直接返回
  if (path.startsWith("http")) return path;
  
  // 如果路径以 / 开头，是相对路径，直接返回（浏览器会自动使用当前域名，Vite代理会处理）
  // 这样 /uploads/covers/... 会通过 Vite 代理转发到后端
  if (path.startsWith("/")) {
    return path;
  }
  
  // 对于非相对路径，使用配置的base URL
  const base =
    import.meta.env.VITE_FILE_BASE_URL ||
    (import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1$/, "")
      : window.location.origin);
  return `${base}/${path}`.replace(/\/+/g, '/'); // 确保只有一个斜杠
}

