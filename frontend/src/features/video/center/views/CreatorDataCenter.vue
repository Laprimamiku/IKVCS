<template>
  <div class="creator-data-center">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon class="title-icon"><DataAnalysis /></el-icon>
        数据中心
      </h1>
      <div class="page-desc">查看您的视频数据统计和分析</div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-section">
      <StatCard :value="totalVideos.toString()" label="总视频数" icon="VideoCamera" variant="primary" />
      <StatCard :value="formatNumber(totalViews)" label="总播放量" icon="View" variant="success" />
      <StatCard :value="formatNumber(totalLikes)" label="总点赞数" icon="CircleCheckFilled" variant="warning" />
      <StatCard :value="formatNumber(totalComments)" label="总评论数" icon="ChatDotRound" variant="default" />
      <StatCard :value="formatNumber(totalCollects)" label="总收藏数" icon="Star" variant="info" />
    </div>

    <!-- 图表区域 -->
    <div class="charts-section">
      <div class="chart-card">
        <div class="chart-header">
          <h3>播放量趋势</h3>
          <el-select v-model="viewChartPeriod" size="small" style="width: 120px">
            <el-option label="最近7天" value="7d" />
            <el-option label="最近30天" value="30d" />
            <el-option label="最近90天" value="90d" />
          </el-select>
        </div>
        <v-chart class="chart" :option="viewChartOption" />
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>互动数据对比</h3>
        </div>
        <v-chart class="chart" :option="interactionChartOption" />
      </div>

      <div class="chart-card">
        <div class="chart-header">
          <h3>视频分类分布</h3>
        </div>
        <v-chart class="chart" :option="categoryChartOption" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { LineChart, BarChart, PieChart } from "echarts/charts";
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { DataAnalysis, VideoCamera, View, CircleCheckFilled, ChatDotRound, Star } from "@element-plus/icons-vue";
import StatCard from "@/shared/components/atoms/StatCard.vue";
import { formatNumber } from "@/shared/utils/formatters";
import type { Video } from "@/shared/types/entity";

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
]);

const props = defineProps<{
  videos: Video[];
}>();

const viewChartPeriod = ref("30d");

// 统计数据
const totalVideos = computed(() => props.videos.length);
const totalViews = computed(() => props.videos.reduce((sum, v) => sum + (v.view_count || 0), 0));
const totalLikes = computed(() => props.videos.reduce((sum, v) => sum + (v.like_count || 0), 0));
const totalComments = computed(() => props.videos.reduce((sum, v) => sum + (v.comment_count || 0), 0));
const totalCollects = computed(() => props.videos.reduce((sum, v) => sum + (v.collect_count || 0), 0));

// 播放量趋势图
const viewChartOption = computed(() => {
  // 模拟最近30天的数据
  const days = 30;
  const dates = [];
  const views = [];
  
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    dates.push(`${date.getMonth() + 1}/${date.getDate()}`);
    views.push(Math.floor(Math.random() * 100) + 50);
  }

  return {
    tooltip: {
      trigger: "axis",
    },
    xAxis: {
      type: "category",
      data: dates,
      boundaryGap: false,
    },
    yAxis: {
      type: "value",
      name: "播放量",
    },
    series: [
      {
        name: "播放量",
        type: "line",
        data: views,
        smooth: true,
        areaStyle: {
          color: {
            type: "linear",
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: "rgba(0, 174, 236, 0.3)" },
              { offset: 1, color: "rgba(0, 174, 236, 0.1)" },
            ],
          },
        },
        itemStyle: {
          color: "#00AEEC",
        },
      },
    ],
  };
});

// 互动数据对比图
const interactionChartOption = computed(() => {
  const topVideos = [...props.videos]
    .sort((a, b) => (b.view_count || 0) - (a.view_count || 0))
    .slice(0, 5);

  return {
    tooltip: {
      trigger: "axis",
      axisPointer: {
        type: "shadow",
      },
    },
    legend: {
      data: ["播放量", "点赞数", "评论数"],
    },
    xAxis: {
      type: "category",
      data: topVideos.map((v) => v.title.substring(0, 10) + "..."),
    },
    yAxis: {
      type: "value",
    },
    series: [
      {
        name: "播放量",
        type: "bar",
        data: topVideos.map((v) => v.view_count || 0),
        itemStyle: { color: "#00AEEC" },
      },
      {
        name: "点赞数",
        type: "bar",
        data: topVideos.map((v) => v.like_count || 0),
        itemStyle: { color: "#FB7299" },
      },
      {
        name: "评论数",
        type: "bar",
        data: topVideos.map((v) => v.comment_count || 0),
        itemStyle: { color: "#52C41A" },
      },
    ],
  };
});

// 分类分布图
const categoryChartOption = computed(() => {
  const categoryMap = new Map<string, number>();
  props.videos.forEach((v) => {
    const category = v.category?.name || "未分类";
    categoryMap.set(category, (categoryMap.get(category) || 0) + 1);
  });

  return {
    tooltip: {
      trigger: "item",
    },
    legend: {
      orient: "vertical",
      left: "left",
    },
    series: [
      {
        name: "视频数量",
        type: "pie",
        radius: "50%",
        data: Array.from(categoryMap.entries()).map(([name, value]) => ({
          value,
          name,
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: "rgba(0, 0, 0, 0.5)",
          },
        },
      },
    ],
  };
});
</script>

<style lang="scss" scoped>
.creator-data-center {
  width: 100%;
}

.page-header {
  margin-bottom: var(--space-6);
  
  .page-title {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-3xl);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
    margin: 0 0 var(--space-2);
    
    .title-icon {
      font-size: var(--font-size-4xl);
      color: var(--bili-blue);
    }
  }
  
  .page-desc {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
  }
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: var(--space-6);
}

.chart-card {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-6);
  box-shadow: var(--shadow-sm);
  
  .chart-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-4);
    
    h3 {
      font-size: var(--font-size-lg);
      font-weight: var(--font-weight-medium);
      color: var(--text-primary);
      margin: 0;
    }
  }
  
  .chart {
    height: 300px;
    width: 100%;
  }
}

@media (max-width: 1200px) {
  .charts-section {
    grid-template-columns: 1fr;
  }
}
</style>




















