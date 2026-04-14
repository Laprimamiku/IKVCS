<template>
  <div class="data-analysis">
    <section class="hero-shell">
      <div class="hero-main">
        <div class="hero-copy">
          <div class="hero-kicker">单视频治理面板</div>
          <h1 class="hero-title">数据分析</h1>
          <p class="hero-desc">用更直观的图表查看当前视频的互动质量、情感倾向、风险分布和 AI 治理效果。</p>
        </div>
        <div class="hero-actions">
          <el-button class="refresh-btn" @click="fetchData" :loading="loading">
            刷新数据
          </el-button>
        </div>
      </div>

      <div v-if="!loading && data" class="hero-metrics-strip">
        <div class="metric-chip metric-chip--blue">
          <span class="chip-label">治理总分</span>
          <strong class="chip-value">{{ overview.governance_score ?? 0 }}</strong>
        </div>
        <div class="metric-chip metric-chip--cyan">
          <span class="chip-label">质量分</span>
          <strong class="chip-value">{{ overview.quality_score ?? 0 }}</strong>
        </div>
        <div class="metric-chip metric-chip--pink">
          <span class="chip-label">风险安全分</span>
          <strong class="chip-value">{{ overview.risk_score ?? 0 }}</strong>
        </div>
        <div class="metric-chip metric-chip--gold">
          <span class="chip-label">AI 覆盖</span>
          <strong class="chip-value">{{ formatPercent(overview.ai_coverage_rate) }}</strong>
        </div>
        <div class="metric-chip metric-chip--green">
          <span class="chip-label">高质曝光</span>
          <strong class="chip-value">{{ formatPercent(overview.highlight_rate) }}</strong>
        </div>
      </div>
    </section>

    <div v-if="loading" class="loading-shell">
      <div class="loading-panel">
        <el-skeleton :rows="8" animated />
      </div>
    </div>

    <div v-else-if="error || !data" class="empty-shell">
      <div class="empty-panel">
        <el-empty :description="error || '暂无数据'">
          <el-button class="refresh-btn" @click="fetchData">重新获取</el-button>
        </el-empty>
      </div>
    </div>

    <template v-else>
      <section class="top-analysis-grid">
        <div class="panel panel--radar">
          <div class="panel-head">
            <div>
              <h3>治理雷达</h3>
              <p>从质量、风险、覆盖和高质曝光四个维度看整体表现</p>
            </div>
          </div>
          <v-chart class="chart chart--large" :option="radarChartOption" autoresize />
        </div>

        <div class="panel panel--summary">
          <div class="panel-head">
            <div>
              <h3>治理摘要与分数对比</h3>
              <p>摘要负责快速理解现状，分数图负责横向比较三项核心指标</p>
            </div>
          </div>

          <div class="summary-combo">
            <div class="summary-main">
              <div class="summary-scoreboard">
                <div class="score-pill">
                  <span>互动总量</span>
                  <strong>{{ overview.total_interactions ?? totalInteractions }}</strong>
                </div>
                <div class="score-pill">
                  <span>风险率</span>
                  <strong>{{ formatPercent(overview.risk_rate) }}</strong>
                </div>
                <div class="score-pill">
                  <span>低质率</span>
                  <strong>{{ formatPercent(overview.low_quality_rate) }}</strong>
                </div>
                <div class="score-pill">
                  <span>节省人工</span>
                  <strong>{{ formatPercent(overview.auto_review_saving_rate) }}</strong>
                </div>
              </div>

              <p class="summary-text">{{ data.summary || '当前视频已完成治理汇总，可结合右侧分数对比和下方图表查看详细结构。' }}</p>

              <div v-if="actions.length" class="action-list">
                <div v-for="(action, index) in actions" :key="`${action.title}-${index}`" class="action-item" :class="`action-item--${action.type || 'default'}`">
                  <div class="action-title">{{ action.title }}</div>
                  <div class="action-detail">{{ action.detail }}</div>
                </div>
              </div>
              <div v-else class="action-empty">当前视频没有额外治理建议，整体状态较稳定。</div>
            </div>

            <div class="summary-chart-wrap">
              <div class="mini-chart-head">
                <h4>治理分数对比</h4>
                <p>治理总分、质量分、风险安全分共用同一百分制坐标轴</p>
              </div>
              <v-chart class="chart chart--summary" :option="scoreCompareOption" autoresize />
            </div>
          </div>
        </div>
      </section>

      <section class="chart-grid chart-grid--main">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>质量分布柱状图</h3>
              <p>比进度条更直观看出高低分段占比</p>
            </div>
          </div>
          <v-chart class="chart" :option="scoreBucketOption" autoresize />
        </div>

        <div class="panel">
          <div class="panel-head">
            <div>
              <h3>情感倾向环图</h3>
              <p>一眼看到正向、中性、负向互动结构</p>
            </div>
          </div>
          <v-chart class="chart" :option="sentimentDonutOption" autoresize />
        </div>
      </section>


      <section class="table-grid">
        <div class="panel panel--table">
          <div class="panel-head">
            <div>
              <h3>高质量互动内容</h3>
              <p>适合被优先展示的评论与弹幕</p>
            </div>
            <el-tag type="success" effect="light">{{ highlightItems.length }} 条</el-tag>
          </div>

          <el-table v-if="highlightItems.length" :data="highlightItems" stripe class="bili-table">
            <el-table-column prop="content" label="内容" min-width="220" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" width="90">
              <template #default="scope">
                <el-tag size="small" :type="scope.row.type === 'danmaku' ? 'primary' : 'success'">
                  {{ scope.row.type === 'danmaku' ? '弹幕' : '评论' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="评分" width="88" align="center">
              <template #default="scope">
                <span class="score-text" :style="{ color: getScoreColor(scope.row.score) }">{{ scope.row.score }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="理由" width="180" show-overflow-tooltip />
            <el-table-column prop="time" label="时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.time) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无高质量内容" :image-size="90" />
        </div>

        <div class="panel panel--table panel--risk">
          <div class="panel-head">
            <div>
              <h3>风险 / 违规预警</h3>
              <p>保留表格，方便创作者逐条复查</p>
            </div>
            <el-tag type="danger" effect="light">{{ risks.length }} 条</el-tag>
          </div>

          <el-table v-if="risks.length" :data="risks" stripe class="bili-table">
            <el-table-column prop="content" label="内容" min-width="220" show-overflow-tooltip />
            <el-table-column prop="reason" label="原因" width="140">
              <template #default="scope">
                <el-tag type="danger" size="small">{{ scope.row.reason }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="AI评分" width="88" align="center">
              <template #default="scope">
                <span class="score-text score-text--risk">{{ scope.row.score }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="time" label="时间" width="180">
              <template #default="scope">
                {{ formatTime(scope.row.time) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无风险内容" :image-size="90" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { use } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { BarChart, PieChart, RadarChart } from "echarts/charts";
import {
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
} from "echarts/components";
import VChart from "vue-echarts";
import { videoApi } from "@/features/video/shared/api/video.api";

use([
  CanvasRenderer,
  BarChart,
  PieChart,
  RadarChart,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  RadarComponent,
]);

type AnalysisItem = {
  content: string;
  type?: "danmaku" | "comment";
  score: number;
  reason: string;
  time: string;
};

type GovernanceAction = {
  type?: string;
  title: string;
  detail: string;
};

type AnalysisResponse = {
  summary?: string;
  sentiment?: {
    positive: number;
    neutral: number;
    negative: number;
  };
  risks?: AnalysisItem[];
  governance?: {
    overview?: {
      total_interactions?: number;
      ai_coverage_rate?: number;
      quality_score?: number;
      risk_score?: number;
      governance_score?: number;
      risk_rate?: number;
      low_quality_rate?: number;
      highlight_rate?: number;
      auto_review_saving_rate?: number;
    };
    distribution?: {
      score_buckets?: Record<string, number>;
    };
    exposure?: {
      items?: AnalysisItem[];
    };
    sources?: {
      distribution?: Record<string, number>;
      coverage_rate?: number;
    };
    actions?: GovernanceAction[];
  };
};

const route = useRoute();
const loading = ref(true);
const error = ref("");
const data = ref<AnalysisResponse | null>(null);

const governance = computed(() => data.value?.governance || {});
const overview = computed(() => governance.value?.overview || {});
const distribution = computed<Record<string, number>>(() => governance.value?.distribution?.score_buckets || {});
const highlightItems = computed<AnalysisItem[]>(() => governance.value?.exposure?.items || []);
const risks = computed<AnalysisItem[]>(() => data.value?.risks || []);
const actions = computed<GovernanceAction[]>(() => governance.value?.actions || []);
const sentiment = computed(() => data.value?.sentiment || { positive: 0, neutral: 0, negative: 0 });

const totalSentimentCount = computed(() => sentiment.value.positive + sentiment.value.neutral + sentiment.value.negative);
const totalInteractions = computed(() => overview.value.total_interactions ?? totalSentimentCount.value ?? 0);

const formatPercent = (val: number | null | undefined) => {
  if (val === null || val === undefined) return "0%";
  return `${(val * 100).toFixed(1)}%`;
};

const formatTime = (time: string | Date) => {
  if (!time) return "-";
  const date = new Date(time);
  return date.toLocaleString("zh-CN");
};

const getScoreColor = (score: number) => {
  if (score >= 80) return "#00aeec";
  if (score >= 60) return "#23ade5";
  if (score >= 40) return "#fb7299";
  return "#ff5c7c";
};

const scoreBucketOption = computed(() => ({
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  grid: { left: 36, right: 18, top: 24, bottom: 28 },
  xAxis: {
    type: "category",
    data: ["0-39", "40-59", "60-79", "80-100"],
    axisLine: { lineStyle: { color: "#d7dbe3" } },
    axisTick: { show: false },
    axisLabel: { color: "#61666d" },
  },
  yAxis: {
    type: "value",
    splitLine: { lineStyle: { color: "#eef1f6" } },
    axisLabel: { color: "#9499a0" },
  },
  series: [
    {
      type: "bar",
      barWidth: 34,
      data: [
        distribution.value["0_39"] || 0,
        distribution.value["40_59"] || 0,
        distribution.value["60_79"] || 0,
        distribution.value["80_100"] || 0,
      ],
      itemStyle: {
        borderRadius: [10, 10, 0, 0],
        color: (params: { dataIndex: number }) => ["#ff6b81", "#ffb347", "#52a3ff", "#2ac3a2"][params.dataIndex],
      },
      label: {
        show: true,
        position: "top",
        color: "#18191c",
        fontWeight: 700,
      },
    },
  ],
}));

const sentimentDonutOption = computed(() => ({
  tooltip: { trigger: "item" },
  legend: {
    bottom: 0,
    itemWidth: 10,
    itemHeight: 10,
    textStyle: { color: "#61666d" },
  },
  series: [
    {
      type: "pie",
      radius: ["48%", "72%"],
      center: ["50%", "45%"],
      avoidLabelOverlap: true,
      itemStyle: {
        borderRadius: 10,
        borderColor: "#fff",
        borderWidth: 4,
      },
      label: {
        formatter: ({ name, percent }: { name: string; percent: number }) => `${name}\n${percent || 0}%`,
        color: "#18191c",
        fontWeight: 600,
      },
      data: [
        { value: sentiment.value.positive, name: "正向", itemStyle: { color: "#2ac3a2" } },
        { value: sentiment.value.neutral, name: "中性", itemStyle: { color: "#52a3ff" } },
        { value: sentiment.value.negative, name: "负向", itemStyle: { color: "#fb7299" } },
      ],
    },
  ],
}));


const scoreCompareOption = computed(() => ({
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  grid: { left: 28, right: 16, top: 24, bottom: 24 },
  xAxis: {
    type: "category",
    data: ["治理总分", "质量分", "风险安全分"],
    axisTick: { show: false },
    axisLine: { lineStyle: { color: "#d7dbe3" } },
    axisLabel: { color: "#61666d" },
  },
  yAxis: {
    type: "value",
    max: 100,
    splitLine: { lineStyle: { color: "#eef1f6" } },
    axisLabel: { color: "#9499a0" },
  },
  series: [
    {
      type: "bar",
      data: [overview.value.governance_score ?? 0, overview.value.quality_score ?? 0, overview.value.risk_score ?? 0],
      barWidth: 38,
      itemStyle: {
        borderRadius: [12, 12, 0, 0],
        color: (params: { dataIndex: number }) => ["#00aeec", "#2ac3a2", "#fb7299"][params.dataIndex],
      },
      label: {
        show: true,
        position: "top",
        color: "#18191c",
        fontWeight: 700,
      },
    },
  ],
}));

const radarChartOption = computed(() => ({
  tooltip: {},
  radar: {
    radius: "65%",
    splitNumber: 4,
    axisName: { color: "#61666d", fontWeight: 600 },
    splitArea: {
      areaStyle: {
        color: ["rgba(0, 174, 236, 0.04)", "rgba(251, 114, 153, 0.03)", "rgba(0, 174, 236, 0.04)", "rgba(251, 114, 153, 0.03)"],
      },
    },
    splitLine: { lineStyle: { color: "rgba(148, 153, 160, 0.18)" } },
    axisLine: { lineStyle: { color: "rgba(148, 153, 160, 0.18)" } },
    indicator: [
      { name: "治理总分", max: 100 },
      { name: "质量分", max: 100 },
      { name: "风险安全分", max: 100 },
      { name: "AI覆盖率", max: 100 },
      { name: "高质曝光率", max: 100 },
    ],
  },
  series: [
    {
      type: "radar",
      data: [
        {
          value: [
            overview.value.governance_score ?? 0,
            overview.value.quality_score ?? 0,
            overview.value.risk_score ?? 0,
            Math.round((overview.value.ai_coverage_rate ?? 0) * 100),
            Math.round((overview.value.highlight_rate ?? 0) * 100),
          ],
          areaStyle: {
            color: "rgba(0, 174, 236, 0.18)",
          },
          lineStyle: {
            color: "#00aeec",
            width: 3,
          },
          itemStyle: {
            color: "#fb7299",
          },
          symbolSize: 8,
        },
      ],
    },
  ],
}));

const fetchData = async () => {
  const videoId = Number(route.params.videoId);
  if (!videoId) {
    error.value = "无效的视频ID";
    loading.value = false;
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const res = await videoApi.getAnalysis(videoId);
    if (res.success) {
      data.value = (res.data || null) as AnalysisResponse | null;
    } else {
      error.value = res.message || "获取数据失败";
    }
  } catch (err: any) {
    console.error(err);
    if (err.response?.status === 401) {
      error.value = "未授权访问";
      ElMessage.warning("请登录");
    } else {
      error.value = "获取分析数据失败";
    }
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.data-analysis {
  min-height: 100%;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(0, 174, 236, 0.12), transparent 30%),
    radial-gradient(circle at top right, rgba(251, 114, 153, 0.12), transparent 28%),
    linear-gradient(180deg, #f8fbff 0%, #f5f7fb 100%);
}

.hero-shell {
  position: relative;
  overflow: hidden;
  margin-bottom: 24px;
  padding: 28px 28px 20px;
  border: 1px solid rgba(255, 255, 255, 0.92);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(255, 255, 255, 0.9)),
    linear-gradient(120deg, rgba(0, 174, 236, 0.08), rgba(251, 114, 153, 0.08));
  box-shadow: 0 18px 40px rgba(15, 34, 58, 0.08);
}

.hero-shell::after {
  content: "";
  position: absolute;
  inset: auto -80px -90px auto;
  width: 240px;
  height: 240px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(0, 174, 236, 0.18) 0%, rgba(0, 174, 236, 0) 70%);
}

.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(0, 174, 236, 0.12);
  color: #00aeec;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.hero-title {
  margin: 12px 0 8px;
  font-size: 34px;
  line-height: 1.08;
  color: #18191c;
}

.hero-desc {
  max-width: 720px;
  margin: 0;
  color: #61666d;
  font-size: 14px;
  line-height: 1.7;
}

.refresh-btn {
  min-width: 112px;
  border: none;
  border-radius: 999px;
  color: #fff;
  background: linear-gradient(135deg, #00aeec, #3bc9f5);
  box-shadow: 0 10px 20px rgba(0, 174, 236, 0.2);
}

.refresh-btn:hover {
  color: #fff;
  background: linear-gradient(135deg, #0397cd, #2eb8e0);
}

.hero-metrics-strip {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-top: 22px;
}

.metric-chip {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(255, 255, 255, 0.88);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.metric-chip--blue { box-shadow: inset 3px 0 0 #00aeec; }
.metric-chip--cyan { box-shadow: inset 3px 0 0 #2ac3a2; }
.metric-chip--pink { box-shadow: inset 3px 0 0 #fb7299; }
.metric-chip--gold { box-shadow: inset 3px 0 0 #ffb347; }
.metric-chip--green { box-shadow: inset 3px 0 0 #5ccf8b; }

.chip-label {
  display: block;
  margin-bottom: 6px;
  color: #9499a0;
  font-size: 12px;
}

.chip-value {
  color: #18191c;
  font-size: 24px;
  font-weight: 700;
}

.loading-shell,
.empty-shell {
  padding: 8px 0 0;
}

.loading-panel,
.empty-panel,
.panel {
  border-radius: 24px;
  border: 1px solid rgba(223, 229, 238, 0.8);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 18px 34px rgba(15, 34, 58, 0.06);
}

.loading-panel,
.empty-panel {
  padding: 24px;
}

.top-analysis-grid,
.chart-grid,
.table-grid {
  display: grid;
  gap: 20px;
}

.top-analysis-grid {
  grid-template-columns: minmax(0, 1.2fr) minmax(340px, 0.8fr);
  margin-bottom: 20px;
}

.chart-grid {
  margin-bottom: 20px;
}

.chart-grid--main {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chart-grid--secondary {
  grid-template-columns: 1.1fr 0.9fr;
}

.table-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.panel {
  padding: 22px 22px 18px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.panel-head h3 {
  margin: 0 0 6px;
  color: #18191c;
  font-size: 18px;
}

.panel-head p {
  margin: 0;
  color: #9499a0;
  font-size: 13px;
}

.chart {
  width: 100%;
  height: 320px;
}

.chart--large {
  height: 380px;
}

.chart--summary {
  height: 300px;
}

.panel--summary,
.panel--radar,
.panel--table {
  min-width: 0;
}

.panel--risk {
  position: relative;
}

.summary-combo {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.85fr);
  gap: 18px;
  align-items: stretch;
}

.summary-main {
  min-width: 0;
}

.summary-chart-wrap {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 16px;
  border-radius: 20px;
  background: linear-gradient(180deg, #fbfdff 0%, #f4f8fc 100%);
  border: 1px solid rgba(223, 229, 238, 0.9);
}

.mini-chart-head {
  margin-bottom: 10px;
}

.mini-chart-head h4 {
  margin: 0 0 6px;
  color: #18191c;
  font-size: 15px;
  font-weight: 700;
}

.mini-chart-head p {
  margin: 0;
  color: #9499a0;
  font-size: 12px;
  line-height: 1.6;
}

.summary-scoreboard {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.score-pill {
  padding: 14px 16px;
  border-radius: 16px;
  background: linear-gradient(180deg, #fbfcfe, #f4f7fb);
}

.score-pill span {
  display: block;
  color: #9499a0;
  font-size: 12px;
}

.score-pill strong {
  display: block;
  margin-top: 6px;
  color: #18191c;
  font-size: 24px;
}

.summary-text {
  margin: 0 0 16px;
  color: #4e5969;
  line-height: 1.8;
}

.action-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.action-item {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(223, 229, 238, 0.9);
  background: #fafcff;
}

.action-item--risk {
  background: linear-gradient(135deg, rgba(251, 114, 153, 0.08), rgba(255, 255, 255, 0.96));
}

.action-item--highlight {
  background: linear-gradient(135deg, rgba(42, 195, 162, 0.08), rgba(255, 255, 255, 0.96));
}

.action-item--coverage {
  background: linear-gradient(135deg, rgba(0, 174, 236, 0.08), rgba(255, 255, 255, 0.96));
}

.action-title {
  margin-bottom: 4px;
  color: #18191c;
  font-size: 14px;
  font-weight: 700;
}

.action-detail,
.action-empty {
  color: #61666d;
  font-size: 13px;
  line-height: 1.7;
}

.score-text {
  font-weight: 700;
}

.score-text--risk {
  color: #fb7299;
}

:deep(.bili-table.el-table) {
  --el-table-border-color: #edf1f7;
  --el-table-header-bg-color: #f8fbff;
  --el-table-row-hover-bg-color: #f6fbff;
  border-radius: 16px;
  overflow: hidden;
}

:deep(.bili-table .el-table__header th) {
  color: #61666d;
  font-weight: 700;
}

@media (max-width: 1200px) {
  .hero-metrics-strip,
  .chart-grid--main,
  .chart-grid--secondary,
  .table-grid,
  .top-analysis-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .data-analysis {
    padding: 16px;
  }

  .hero-shell,
  .panel,
  .loading-panel,
  .empty-panel {
    border-radius: 18px;
  }

  .hero-main {
    flex-direction: column;
  }

  .hero-title {
    font-size: 28px;
  }

  .summary-combo {
    grid-template-columns: 1fr;
  }

  .summary-chart-wrap {
    padding: 14px;
    border-radius: 16px;
  }

  .summary-scoreboard {
    grid-template-columns: 1fr;
  }

  .chart,
  .chart--large,
  .chart--summary {
    height: 280px;
  }
}
</style>
