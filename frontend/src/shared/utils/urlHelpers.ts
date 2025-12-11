// 解析文件 URL，支持相对路径与完整 URL
export function resolveFileUrl(path: string | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  // 优先使用文件基础域名；否则使用当前站点，避免开发环境的跨域访问
  const base =
    import.meta.env.VITE_FILE_BASE_URL ||
    window.location.origin ||
    (import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1$/, "")
      : "");
  return `${base}${path}`;
}

