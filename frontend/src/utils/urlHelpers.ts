// 解析文件 URL，支持相对路径与完整 URL
export function resolveFileUrl(path: string | undefined): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  const base =
    import.meta.env.VITE_FILE_BASE_URL ||
    (import.meta.env.VITE_API_BASE_URL
      ? import.meta.env.VITE_API_BASE_URL.replace(/\/api\/v1$/, "")
      : window.location.origin);
  return `${base}${path}`;
}

