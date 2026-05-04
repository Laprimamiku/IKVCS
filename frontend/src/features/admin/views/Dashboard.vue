<template>
  <div class="bili-dashboard">
    <div class="dashboard-toolbar">
      <div class="toolbar-info">
        <el-icon><DataAnalysis /></el-icon>
        <span>默认自动刷新：关闭（仅首次加载）</span>
        <span class="last-refresh">最近刷新：{{ lastRefreshText }}</span>
      </div>
      <div class="toolbar-actions">
        <el-radio-group v-model="selectedTrendDays" size="small" @change="handleTrendWindowChange">
          <el-radio-button :label="7">近一周</el-radio-button>
          <el-radio-button :label="30">近一月</el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <div class="stat-card users">
        <el-icon class="stat-icon"><UserFilled /></el-icon>
        <div class="stat-content">
          <div class="stat-value">{{ overview.total_users }}</div>
          <div class="stat-label">总用户数</div>
          <div class="stat-trend up">
            <span class="trend-icon">↑</span>
            今日 +{{ overview.new_users_today }}
          </div>
        </div>
      </div>

      <div class="stat-card videos">
        <el-icon class="stat-icon"><VideoCamera /></el-icon>
        <div class="stat-content">
          <div class="stat-value">{{ overview.total_videos }}</div>
          <div class="stat-label">已发布视频</div>
          <div class="stat-trend up">
            <span class="trend-icon">↑</span>
            今日 +{{ overview.new_videos_today }}
          </div>
        </div>
      </div>

      <div class="stat-card reports">
        <el-icon class="stat-icon"><Warning /></el-icon>
        <div class="stat-content">
          <div class="stat-value">{{ overview.total_reports_pending }}</div>
          <div class="stat-label">待处理举报</div>
          <div class="stat-trend warning">
            <span class="trend-icon">!</span>
            需尽快处理
          </div>
        </div>
      </div>

      <div class="stat-card active">
        <el-icon class="stat-icon"><TrendCharts /></el-icon>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(overview.active_users_today || 0) }}</div>
          <div class="stat-label">今日活跃</div>
          <div class="stat-trend up">
            <span class="trend-icon">↑</span>
            实时统计
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="charts-grid">
      <!-- Trend Chart -->
      <div class="chart-card trend-chart">
        <div class="card-header">
          <h3 class="card-title">
            <el-icon class="title-icon"><DataAnalysis /></el-icon>
            数据趋势 (近{{ selectedTrendDays }}天)
          </h3>
          <div class="chart-legend">
            <span class="legend-item users">
              <span class="legend-dot"></span>
              新增用户
            </span>
            <span class="legend-item videos">
              <span class="legend-dot"></span>
              新增视频
            </span>
          </div>
        </div>
        <div class="card-body">
          <div v-if="trends.length && selectedTrendDays === 7" class="bar-chart">
            <div v-for="item in trends" :key="item.date" class="bar-group">
              <div class="bars">
                <div 
                  class="bar users" 
                  :style="{ height: getBarHeight(item.user_count, maxTrendCount) }"
                  :title="`用户: ${item.user_count}`"
                >
                  <span class="bar-value">{{ item.user_count }}</span>
                </div>
                <div 
                  class="bar videos" 
                  :style="{ height: getBarHeight(item.video_count, maxTrendCount) }"
                  :title="`视频: ${item.video_count}`"
                >
                  <span class="bar-value">{{ item.video_count }}</span>
                </div>
              </div>
              <div class="bar-label">{{ formatDate(item.date) }}</div>
            </div>
          </div>
          <div v-else-if="trends.length && selectedTrendDays === 30" class="line-chart-wrap">
            <svg class="line-chart" viewBox="0 0 1000 260" preserveAspectRatio="none" role="img" aria-label="近30天用户和视频趋势折线图">
              <polygon class="area users" :points="userAreaPoints" />
              <polygon class="area videos" :points="videoAreaPoints" />
              <polyline
                class="line users"
                :points="userLinePoints"
              />
              <polyline
                class="line videos"
                :points="videoLinePoints"
              />
              <circle
                v-for="(p, idx) in userPoints"
                :key="`u-${idx}`"
                v-show="p.value > 0"
                class="point users"
                :cx="p.x"
                :cy="p.y"
                r="3.5"
              />
              <circle
                v-for="(p, idx) in videoPoints"
                :key="`v-${idx}`"
                v-show="p.value > 0"
                class="point videos"
                :cx="p.x"
                :cy="p.y"
                r="3.5"
              />
              <g
                v-for="item in lineHoverItems"
                :key="`h-${item.idx}`"
                class="hover-target"
              >
                <line :x1="item.x" :x2="item.x" y1="8" y2="232" />
                <circle :cx="item.x" :cy="224" r="8" />
                <title>{{ item.tooltip }}</title>
              </g>
            </svg>
            <div class="line-x-axis">
              <span
                v-for="tick in lineAxisTicks"
                :key="`tick-${tick.idx}`"
                class="x-label"
              >
                {{ formatDate(tick.date) }}
              </span>
            </div>
          </div>
          <div v-else class="chart-empty">暂无数据</div>
        </div>
      </div>

      <!-- Category Distribution -->
      <div class="chart-card category-chart">
        <div class="card-header">
          <h3 class="card-title">
            <el-icon class="title-icon"><TrendCharts /></el-icon>
            分类分布
          </h3>
        </div>
        <div class="card-body">
          <div v-if="categories.length" class="category-donut-wrap">
            <svg
              class="category-donut"
              viewBox="0 0 240 240"
              role="img"
              aria-label="分类分布环形图"
            >
              <circle class="donut-track" cx="120" cy="120" r="80" />
              <circle
                v-for="seg in categorySegments"
                :key="seg.name"
                class="donut-segment"
                cx="120"
                cy="120"
                r="80"
                :stroke="seg.color"
                :stroke-dasharray="`${seg.length} ${seg.gap}`"
                :stroke-dashoffset="seg.offset"
              >
                <title>{{ `${seg.name}: ${seg.count}（${seg.ratio.toFixed(1)}%）` }}</title>
              </circle>
              <text x="120" y="112" text-anchor="middle" class="donut-center-label">总数</text>
              <text x="120" y="136" text-anchor="middle" class="donut-center-value">{{ categoryTotal }}</text>
            </svg>
          </div>
          <div v-else class="chart-empty">暂无数据</div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <h3 class="section-title">
        <el-icon class="title-icon"><DataAnalysis /></el-icon>
        快捷操作
      </h3>
      <div class="actions-grid">
        <router-link to="/admin/audit" class="action-card">
          <el-icon class="action-icon"><VideoCamera /></el-icon>
          <span class="action-text">审核视频</span>
        </router-link>
        <router-link to="/admin/reports" class="action-card">
          <el-icon class="action-icon"><Warning /></el-icon>
          <span class="action-text">处理举报</span>
        </router-link>
        <router-link to="/admin/users" class="action-card">
          <el-icon class="action-icon"><UserFilled /></el-icon>
          <span class="action-text">管理用户</span>
        </router-link>
        <router-link to="/admin/categories" class="action-card">
          <el-icon class="action-icon"><Folder /></el-icon>
          <span class="action-text">分类管理</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { UserFilled, VideoCamera, Warning, TrendCharts, DataAnalysis, Folder } from "@element-plus/icons-vue";
import {
  adminApi,
  type StatsOverview,
  type ChartData,
  type CategoryStat,
} from "../api/admin.api";

const overview = ref<StatsOverview>({
  total_users: 0,
  new_users_today: 0,
  total_videos: 0,
  new_videos_today: 0,
  total_reports_pending: 0,
});
const trends = ref<ChartData[]>([]);
const categories = ref<CategoryStat[]>([]);
const refreshing = ref(false);
const lastRefreshAt = ref<Date | null>(null);
const selectedTrendDays = ref<7 | 30>(7);

/** 用户与视频共用同一纵轴刻度，便于同一天对比（如 2 与 1 呈 2:1） */
const maxTrendCount = computed(() => {
  if (!trends.value.length) return 1;
  let m = 0;
  for (const t of trends.value) {
    m = Math.max(m, t.user_count || 0, t.video_count || 0);
  }
  return Math.max(m, 1);
});
const lineMaxCount = computed(() => {
  if (!trends.value.length) return 1;
  let max = 0;
  for (const t of trends.value) {
    max = Math.max(max, t.user_count || 0, t.video_count || 0);
  }
  return Math.max(max, 1);
});

const formatNumber = (num: number) => {
  if (num >= 10000) return (num / 10000).toFixed(1) + '万';
  return num.toString();
};

const formatDate = (dateStr: string) => {
  return dateStr.slice(5); // MM-DD
};

const getBarHeight = (value: number, max: number) => {
  if (!value || max <= 0) return "0%";
  const raw = (value / max) * 100;
  // 有数据时至少保留一点高度，避免非零小数值完全看不见；零仍为 0%
  const percentage = Math.max(raw, 3);
  return `${percentage}%`;
};

const categoryTotal = computed(() => categories.value.reduce((sum, c) => sum + Number(c.count || 0), 0));

const categoryPalette = [
  "#00AEEC",
  "#FB7299",
  "#36CFC9",
  "#73D13D",
  "#FAAD14",
  "#9254DE",
  "#597EF7",
  "#13C2C2",
  "#F759AB",
  "#A0D911",
];

const categorySegments = computed(() => {
  const total = categoryTotal.value;
  const circumference = 2 * Math.PI * 80;
  if (!total) return [];

  let acc = 0;
  return categories.value.map((cat, idx) => {
    const count = Number(cat.count || 0);
    const ratio = count / total;
    const length = ratio * circumference;
    const offset = -acc;
    acc += length;
    return {
      name: cat.name,
      count,
      ratio: ratio * 100,
      color: categoryPalette[idx % categoryPalette.length],
      length,
      gap: Math.max(0, circumference - length),
      offset,
    };
  });
});

const lastRefreshText = computed(() => {
  if (!lastRefreshAt.value) return "未刷新";
  const d = lastRefreshAt.value;
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
});

type LinePoint = { x: number; y: number; value: number };

const buildLinePoints = (values: number[]): LinePoint[] => {
  if (!values.length) return [];
  const width = 1000;
  const height = 260;
  const left = 20;
  const right = 980;
  const top = 16;
  const bottom = 232;
  const stepX = values.length > 1 ? (right - left) / (values.length - 1) : 0;
  return values
    .map((v, idx) => {
      const x = left + idx * stepX;
      const y = bottom - (Math.max(0, v) / lineMaxCount.value) * (bottom - top);
      return { x, y, value: Math.max(0, v) };
    });
};

const userPoints = computed(() => buildLinePoints(trends.value.map((t) => Number(t.user_count || 0))));
const videoPoints = computed(() => buildLinePoints(trends.value.map((t) => Number(t.video_count || 0))));

const toSvgPoints = (points: LinePoint[]) => points.map((p) => `${p.x},${p.y}`).join(" ");
const toAreaPoints = (points: LinePoint[]) => {
  if (!points.length) return "";
  const bottom = 232;
  const first = points[0];
  const last = points[points.length - 1];
  return `${first.x},${bottom} ${toSvgPoints(points)} ${last.x},${bottom}`;
};

const userLinePoints = computed(() => toSvgPoints(userPoints.value));
const videoLinePoints = computed(() => toSvgPoints(videoPoints.value));
const userAreaPoints = computed(() => toAreaPoints(userPoints.value));
const videoAreaPoints = computed(() => toAreaPoints(videoPoints.value));

const lineAxisTicks = computed(() => {
  if (!trends.value.length) return [];
  const last = trends.value.length - 1;
  const desired = [0, 7, 14, 21, last]
    .map((i) => Math.min(i, last))
    .filter((v, i, arr) => arr.indexOf(v) === i);
  return desired.map((idx) => ({ idx, date: trends.value[idx].date }));
});

const lineHoverItems = computed(() => {
  return trends.value.map((t, idx) => {
    const point = userPoints.value[idx] || videoPoints.value[idx];
    const date = formatDate(t.date);
    const users = Number(t.user_count || 0);
    const videos = Number(t.video_count || 0);
    return {
      idx,
      x: point?.x ?? 0,
      tooltip: `${date}\n新增用户: ${users}\n新增视频: ${videos}`,
    };
  });
});

const fetchDashboardData = async () => {
  refreshing.value = true;
  try {
    const [resOverview, resTrends, resCats] = await Promise.all([
      adminApi.getOverview(),
      adminApi.getTrends(selectedTrendDays.value),
      adminApi.getCategoryStats(),
    ]);
    
    if (resOverview.success && resOverview.data) {
      overview.value = resOverview.data;
    }
    if (resTrends.success && resTrends.data) {
      trends.value = resTrends.data;
    }
    if (resCats.success && resCats.data) {
      categories.value = resCats.data;
    }
    lastRefreshAt.value = new Date();
  } catch (e) {
    console.error("加载仪表板数据失败:", e);
    ElMessage.error("刷新数据失败，请稍后重试");
  } finally {
    refreshing.value = false;
  }
};

const handleTrendWindowChange = () => {
  void fetchDashboardData();
};

const handleAdminRefresh = () => {
  void fetchDashboardData();
};

onMounted(() => {
  void fetchDashboardData();
  window.addEventListener("admin:refresh", handleAdminRefresh);
});

onUnmounted(() => {
  window.removeEventListener("admin:refresh", handleAdminRefresh);
});
</script>

<style scoped lang="scss">
.bili-dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.dashboard-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-4);
  box-shadow: var(--shadow-card);

  .toolbar-info {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
  }

  .last-refresh {
    color: var(--text-primary);
  }
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

.stat-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  box-shadow: var(--shadow-card);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
  }

  &.users::before { background: var(--bili-blue); }
  &.videos::before { background: var(--primary-color); }
  &.reports::before { background: var(--warning-color); }
  &.active::before { background: var(--success-color); }

  &:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-card-hover);
  }
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  background: var(--bg-gray-1);
  border-radius: var(--radius-lg);
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: var(--font-size-4xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1.2;
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  margin-top: var(--space-1);
}

.stat-trend {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xs);
  margin-top: var(--space-2);
  padding: 2px 8px;
  border-radius: var(--radius-round);

  &.up {
    color: var(--success-color);
    background: var(--success-light);
  }

  &.warning {
    color: var(--warning-color);
    background: var(--warning-light);
  }

  .trend-icon {
    font-style: normal;
  }
}

/* Charts Grid */
.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-4);
}

.chart-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--border-light);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;

  .title-icon {
    font-style: normal;
  }
}

.card-body {
  padding: var(--space-5);
}

/* Chart Legend */
.chart-legend {
  display: flex;
  gap: var(--space-4);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--font-size-xs);
  color: var(--text-secondary);

  .legend-dot {
    width: 8px;
    height: 8px;
    border-radius: var(--radius-circle);
  }

  &.users .legend-dot { background: var(--bili-blue); }
  &.videos .legend-dot { background: var(--primary-color); }
}

/* Bar Chart */
.bar-chart {
  display: flex;
  justify-content: space-around;
  align-items: flex-end;
  height: 200px;
  padding-top: var(--space-4);
}

.bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 160px;
}

.bar {
  width: 24px;
  min-height: 4px;
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  position: relative;
  transition: all var(--transition-base);
  cursor: pointer;

  &.users { background: var(--bili-blue); }
  &.videos { background: var(--primary-color); }

  &:hover {
    opacity: 0.8;

    .bar-value {
      opacity: 1;
      transform: translateY(-4px);
    }
  }

  .bar-value {
    position: absolute;
    top: -20px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 10px;
    color: var(--text-secondary);
    opacity: 0;
    transition: all var(--transition-base);
    white-space: nowrap;
  }
}

.bar-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
}

/* Category Donut */
.category-donut-wrap {
  display: flex;
  justify-content: center;
  align-items: center;
}

.category-donut {
  width: 220px;
  height: 220px;
}

.donut-track {
  fill: none;
  stroke: var(--bg-gray-1);
  stroke-width: 22;
}

.donut-segment {
  fill: none;
  stroke-width: 22;
  transform: rotate(-90deg);
  transform-origin: 120px 120px;
  transition: opacity var(--transition-base), stroke-width var(--transition-base), filter var(--transition-base);
  cursor: pointer;

  &:hover {
    opacity: 0.9;
    stroke-width: 28;
    filter: brightness(1.06);
  }
}

.donut-center-label {
  font-size: 13px;
  fill: var(--text-tertiary);
}

.donut-center-value {
  font-size: 24px;
  font-weight: 700;
  fill: var(--text-primary);
}

.chart-empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-tertiary);
}

.line-chart-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.line-chart {
  width: 100%;
  height: 220px;
  background:
    linear-gradient(to bottom, transparent 24%, rgba(0,0,0,0.035) 25%, transparent 26%) 0 0 / 100% 54px,
    linear-gradient(var(--bg-white), var(--bg-white));
  border-radius: var(--radius-md);
}

.area {
  stroke: none;
}

.area.users {
  fill: rgba(0, 174, 236, 0.08);
}

.area.videos {
  fill: rgba(251, 114, 153, 0.08);
}

.line {
  fill: none;
  stroke-width: 2.5;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.line.users {
  stroke: var(--bili-blue);
}

.line.videos {
  stroke: var(--primary-color);
}

.point {
  stroke: #fff;
  stroke-width: 1.5;
}

.point.users {
  fill: var(--bili-blue);
}

.point.videos {
  fill: var(--primary-color);
}

.hover-target {
  line {
    stroke: transparent;
    stroke-width: 12;
  }

  circle {
    fill: transparent;
  }
}

.line-x-axis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  padding: 0 8px;
}

.x-label {
  font-size: var(--font-size-xs);
  color: var(--text-tertiary);
  text-align: center;
  white-space: nowrap;
  transform: translateY(-2px);
}

/* Quick Actions */
.quick-actions {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  box-shadow: var(--shadow-card);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0 0 var(--space-4);

  .title-icon {
    font-style: normal;
  }
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-4);
}

/* 与 AdminLayout 侧栏 .nav-item 默认 / active风格一致：白底深字，悬停或当前路由为浅粉底+主色 */
.action-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-5);
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  text-decoration: none;
  color: var(--text-primary);
  transition: all var(--transition-base);

  .action-icon {
    font-size: 32px;
    color: var(--text-primary);
  }

  .action-text {
    font-size: var(--font-size-sm);
    color: var(--text-primary);
  }

  &:hover,
  &.router-link-active {
    background: var(--primary-light);
    color: var(--primary-color);

    &::before {
      content: "";
      position: absolute;
      left: 0;
      top: 50%;
      transform: translateY(-50%);
      width: 3px;
      height: 20px;
      background: var(--primary-color);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    }

    .action-icon,
    .action-text {
      color: var(--primary-color);
    }

    .action-text {
      font-weight: var(--font-weight-medium);
    }
  }
}

/* Responsive */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
