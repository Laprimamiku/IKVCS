/**
 * 格式化数字显示（万为单位）
 */
export function formatNumber(num?: number): string {
  if (!num) return '0';
  if (num > 10000) return `${(num / 10000).toFixed(1)}万`;
  return num.toString();
}

/**
 * 格式化日期时间
 */
export function formatDate(dateStr?: string): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const year = date.getFullYear();
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const day = date.getDate().toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * 获取带防缓存参数的封面URL
 */
export function getCoverUrl(coverUrl?: string): string {
  if (!coverUrl) return '';
  return `${coverUrl}?t=${Date.now()}`;
}

