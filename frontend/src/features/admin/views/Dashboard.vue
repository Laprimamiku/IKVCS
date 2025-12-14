<template>
  <div class="dashboard-page">
    <div class="overview-cards">
      <div class="card-item blue">
        <div class="label">总用户数</div>
        <div class="value">{{ overview.total_users }}</div>
        <div class="sub">今日新增 {{ overview.new_users_today }}</div>
      </div>
      <div class="card-item pink">
        <div class="label">已发布视频</div>
        <div class="value">{{ overview.total_videos }}</div>
        <div class="sub">今日新增 {{ overview.new_videos_today }}</div>
      </div>
      <div class="card-item orange">
        <div class="label">待处理举报</div>
        <div class="value">{{ overview.total_reports_pending }}</div>
        <div class="sub">需尽快处理</div>
      </div>
    </div>

    <div class="charts-section">
      <div class="chart-card main-chart">
        <h3>📊 数据趋势 (近7天)</h3>
        <div class="chart-placeholder" v-if="trends.length">
          <div class="simple-bar-chart">
            <div v-for="item in trends" :key="item.date" class="bar-group">
              <div class="bars">
                <div
                  class="bar user"
                  :style="{ height: item.user_count * 10 + 'px' }"
                  :title="`用户: ${item.user_count}`"
                ></div>
                <div
                  class="bar video"
                  :style="{ height: item.video_count * 10 + 'px' }"
                  :title="`视频: ${item.video_count}`"
                ></div>
              </div>
              <div class="date">{{ item.date.slice(5) }}</div>
            </div>
          </div>
          <div class="legend">
            <span class="dot user"></span> 新增用户
            <span class="dot video"></span> 新增视频
          </div>
        </div>
      </div>

      <div class="chart-card sub-chart">
        <h3>📂 分类占比</h3>
        <div class="category-list">
          <div v-for="cat in categories" :key="cat.name" class="cat-item">
            <span class="name">{{ cat.name }}</span>
            <div class="progress-bg">
              <div
                class="progress-bar"
                :style="{ width: (cat.count / maxCatCount) * 100 + '%' }"
              ></div>
            </div>
            <span class="count">{{ cat.count }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
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

const maxCatCount = computed(() =>
  Math.max(...categories.value.map((c) => c.count), 1)
);

onMounted(async () => {
  try {
    const [resOverview, resTrends, resCats] = await Promise.all([
      adminApi.getOverview(),
      adminApi.getTrends(),
      adminApi.getCategoryStats(),
    ]);
    
    // 修复：正确解析API响应数据
    if (resOverview.success && resOverview.data) {
      overview.value = resOverview.data;
    }
    if (resTrends.success && resTrends.data) {
      trends.value = resTrends.data;
    }
    if (resCats.success && resCats.data) {
      categories.value = resCats.data;
    }
  } catch (e) {
    console.error('加载仪表板数据失败:', e);
  }
});
</script>

<style scoped lang="scss">
.dashboard-page {
  .overview-cards {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
    margin-bottom: 24px;

    .card-item {
      background: #fff;
      padding: 24px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

      .label {
        color: #999;
        font-size: 14px;
        margin-bottom: 8px;
      }
      .value {
        font-size: 32px;
        font-weight: bold;
        margin-bottom: 8px;
        color: #18191c;
      }
      .sub {
        font-size: 12px;
        opacity: 0.8;
      }

      &.blue {
        border-top: 4px solid #00aeec;
        .sub {
          color: #00aeec;
        }
      }
      &.pink {
        border-top: 4px solid #fb7299;
        .sub {
          color: #fb7299;
        }
      }
      &.orange {
        border-top: 4px solid #ffb027;
        .sub {
          color: #ffb027;
        }
      }
    }
  }

  .charts-section {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 24px;

    .chart-card {
      background: #fff;
      padding: 24px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);

      h3 {
        margin-bottom: 20px;
        font-size: 16px;
        color: #18191c;
      }
    }
  }

  // 简易图表样式
  .simple-bar-chart {
    display: flex;
    justify-content: space-around;
    align-items: flex-end;
    height: 200px;
    border-bottom: 1px solid #eee;
    padding-bottom: 10px;

    .bar-group {
      display: flex;
      flex-direction: column;
      align-items: center;

      .bars {
        display: flex;
        align-items: flex-end;
        gap: 4px;

        .bar {
          width: 20px;
          min-height: 2px;
          border-radius: 2px 2px 0 0;
          &.user {
            background: #00aeec;
          }
          &.video {
            background: #fb7299;
          }
        }
      }
      .date {
        font-size: 12px;
        color: #999;
        margin-top: 8px;
      }
    }
  }

  .category-list {
    .cat-item {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      .name {
        width: 60px;
        font-size: 13px;
        color: #666;
      }
      .progress-bg {
        flex: 1;
        height: 8px;
        background: #f0f0f0;
        border-radius: 4px;
        margin: 0 12px;
        overflow: hidden;

        .progress-bar {
          height: 100%;
          background: #00aeec;
          border-radius: 4px;
        }
      }
      .count {
        width: 40px;
        text-align: right;
        font-size: 13px;
        font-weight: bold;
      }
    }
  }
}
</style>
