<template>
  <div class="bili-dashboard">
    <div class="dashboard-toolbar">
      <div class="toolbar-info">
        <el-icon><DataAnalysis /></el-icon>
        <span>默认自动刷新：关闭（仅首次加载）</span>
        <span class="last-refresh">最近刷新：{{ lastRefreshText }}</span>
      </div>
      <el-button type="primary" :loading="refreshing" @click="fetchDashboardData">
        手动刷新
      </el-button>
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
            数据趋势 (近7天)
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
          <div class="bar-chart" v-if="trends.length">
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
          <div class="category-list">
            <div v-for="cat in categories" :key="cat.name" class="category-item">
              <div class="category-info">
                <span class="category-name">{{ cat.name }}</span>
                <span class="category-count">{{ cat.count }}</span>
              </div>
              <div class="category-bar">
                <div 
                  class="category-progress" 
                  :style="{ width: getCategoryWidth(cat.count) }"
                ></div>
              </div>
            </div>
          </div>
          <div v-if="categories.length === 0" class="chart-empty">暂无数据</div>
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
import { ref, onMounted, computed } from "vue";
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

/** 用户与视频共用同一纵轴刻度，便于同一天对比（如 2 与 1 呈 2:1） */
const maxTrendCount = computed(() => {
  if (!trends.value.length) return 1;
  let m = 0;
  for (const t of trends.value) {
    m = Math.max(m, t.user_count || 0, t.video_count || 0);
  }
  return Math.max(m, 1);
});
const maxCatCount = computed(() => Math.max(...categories.value.map(c => c.count), 1));

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

const getCategoryWidth = (count: number) => {
  const percentage = (count / maxCatCount.value) * 100;
  return `${percentage}%`;
};

const lastRefreshText = computed(() => {
  if (!lastRefreshAt.value) return "未刷新";
  const d = lastRefreshAt.value;
  const h = String(d.getHours()).padStart(2, "0");
  const m = String(d.getMinutes()).padStart(2, "0");
  const s = String(d.getSeconds()).padStart(2, "0");
  return `${h}:${m}:${s}`;
});

const fetchDashboardData = async () => {
  refreshing.value = true;
  try {
    const [resOverview, resTrends, resCats] = await Promise.all([
      adminApi.getOverview(),
      adminApi.getTrends(),
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

onMounted(() => {
  void fetchDashboardData();
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

/* Category List */
.category-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.category-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.category-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category-name {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}

.category-count {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.category-bar {
  height: 8px;
  background: var(--bg-gray-1);
  border-radius: var(--radius-round);
  overflow: hidden;
}

.category-progress {
  height: 100%;
  background: var(--primary-gradient);
  border-radius: var(--radius-round);
  transition: width var(--transition-slow);
}

.chart-empty {
  text-align: center;
  padding: var(--space-8);
  color: var(--text-tertiary);
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
