<template>
  <div class="video-summary-container">
    <div class="summary-header">
      <h3 class="summary-title">
        <el-icon><Document /></el-icon>
        视频摘要
      </h3>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="summary-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <!-- 空状态 -->
    <div v-else-if="!summaryShort && !summaryDetailed && !knowledgePoints" class="summary-empty">
      <el-icon><Document /></el-icon>
      <p>暂无摘要信息</p>
      <el-button
        v-if="showGenerateButton"
        type="primary"
        size="small"
        :loading="generating"
        @click="handleGenerate"
      >
        生成摘要
      </el-button>
    </div>

    <!-- 摘要内容 -->
    <div v-else class="summary-content">
      <!-- 简短摘要 -->
      <div v-if="summaryShort" class="summary-section">
        <div class="section-header">
          <span class="section-title">简短摘要</span>
        </div>
        <div class="section-content">
          {{ summaryShort }}
        </div>
      </div>

      <!-- 详细摘要 -->
      <div v-if="summaryDetailed" class="summary-section">
        <div class="section-header">
          <span class="section-title">详细摘要</span>
          <el-button
            v-if="summaryDetailed.length > 200"
            text
            type="primary"
            size="small"
            @click="detailedExpanded = !detailedExpanded"
          >
            {{ detailedExpanded ? '收起' : '展开' }}
            <el-icon>
              <ArrowDown v-if="!detailedExpanded" />
              <ArrowUp v-else />
            </el-icon>
          </el-button>
        </div>
        <div
          class="section-content"
          :class="{ expanded: detailedExpanded }"
        >
          {{ summaryDetailed }}
        </div>
      </div>

      <!-- 核心知识点 -->
      <div v-if="knowledgePoints && hasKnowledgePoints" class="summary-section knowledge-section">
        <div class="section-header">
          <span class="section-title">核心知识点</span>
        </div>
        <div class="knowledge-content">
          <!-- 概念定义 -->
          <div v-if="knowledgePoints.concepts && knowledgePoints.concepts.length > 0" class="knowledge-group">
            <div class="knowledge-group-title">
              <el-icon><InfoFilled /></el-icon>
              概念定义
            </div>
            <ul class="knowledge-list">
              <li v-for="(concept, index) in knowledgePoints.concepts" :key="index">
                {{ concept }}
              </li>
            </ul>
          </div>

          <!-- 操作步骤 -->
          <div v-if="knowledgePoints.steps && knowledgePoints.steps.length > 0" class="knowledge-group">
            <div class="knowledge-group-title">
              <el-icon><Operation /></el-icon>
              操作步骤
            </div>
            <ol class="knowledge-list steps-list">
              <li v-for="(step, index) in knowledgePoints.steps" :key="index">
                {{ step }}
              </li>
            </ol>
          </div>

          <!-- 关键数据 -->
          <div v-if="knowledgePoints.data && knowledgePoints.data.length > 0" class="knowledge-group">
            <div class="knowledge-group-title">
              <el-icon><DataAnalysis /></el-icon>
              关键数据
            </div>
            <ul class="knowledge-list">
              <li v-for="(data, index) in knowledgePoints.data" :key="index">
                {{ data }}
              </li>
            </ul>
          </div>

          <!-- 重要观点 -->
          <div v-if="knowledgePoints.opinions && knowledgePoints.opinions.length > 0" class="knowledge-group">
            <div class="knowledge-group-title">
              <el-icon><ChatLineRound /></el-icon>
              重要观点
            </div>
            <ul class="knowledge-list">
              <li v-for="(opinion, index) in knowledgePoints.opinions" :key="index">
                {{ opinion }}
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import {
  Document,
  ArrowDown,
  ArrowUp,
  InfoFilled,
  Operation,
  DataAnalysis,
  ChatLineRound,
} from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import type { KnowledgePoints } from '@/shared/types/entity';
import {
  getVideoSummary,
  getVideoKnowledge,
  generateVideoSummary,
} from '@/features/video/shared/api/video.api';

interface Props {
  videoId: number;
  summaryShort?: string; // 从视频数据传入的简短摘要
  summaryDetailed?: string; // 从视频数据传入的详细摘要
  knowledgePoints?: KnowledgePoints; // 从视频数据传入的知识点
  showGenerateButton?: boolean; // 是否显示生成按钮
}

const props = withDefaults(defineProps<Props>(), {
  showGenerateButton: false,
});

const loading = ref(false);
const generating = ref(false);
const detailedExpanded = ref(false);
const summaryShortData = ref<string>('');
const summaryDetailedData = ref<string>('');
const knowledgePointsData = ref<KnowledgePoints | null>(null);

// 使用传入的props或加载的数据
const summaryShort = computed(() => props.summaryShort || summaryShortData.value);
const summaryDetailed = computed(() => props.summaryDetailed || summaryDetailedData.value);
const knowledgePoints = computed(() => props.knowledgePoints || knowledgePointsData.value);

// 判断是否有知识点
const hasKnowledgePoints = computed(() => {
  if (!knowledgePoints.value) return false;
  const kp = knowledgePoints.value;
  return (
    (kp.concepts && kp.concepts.length > 0) ||
    (kp.steps && kp.steps.length > 0) ||
    (kp.data && kp.data.length > 0) ||
    (kp.opinions && kp.opinions.length > 0)
  );
});

// 加载摘要数据
const loadSummary = async () => {
  if (!props.videoId) return;
  
  // 如果已经通过props传入，不需要加载
  if (props.summaryShort || props.summaryDetailed) {
    return;
  }
  
  loading.value = true;
  try {
    const response = await getVideoSummary(props.videoId);
    if (response.success && response.data) {
      summaryShortData.value = response.data.summary_short || '';
      summaryDetailedData.value = response.data.summary_detailed || '';
    }
  } catch (error) {
    console.error('加载视频摘要失败:', error);
  } finally {
    loading.value = false;
  }
};

// 加载知识点
const loadKnowledge = async () => {
  if (!props.videoId) return;
  
  // 如果已经通过props传入，不需要加载
  if (props.knowledgePoints) {
    return;
  }
  
  try {
    const response = await getVideoKnowledge(props.videoId);
    if (response.success && response.data) {
      knowledgePointsData.value = response.data.knowledge_points || null;
    }
  } catch (error) {
    console.error('加载知识点失败:', error);
  }
};

// 生成摘要
const handleGenerate = async () => {
  if (!props.videoId) return;
  
  generating.value = true;
  try {
    const response = await generateVideoSummary(props.videoId);
    if (response.success) {
      ElMessage.success('摘要生成中，请稍后刷新查看');
      // 延迟后重新加载
      setTimeout(() => {
        loadSummary();
        loadKnowledge();
      }, 2000);
    } else {
      ElMessage.error('生成摘要失败');
    }
  } catch (error) {
    console.error('生成摘要失败:', error);
    ElMessage.error('生成摘要失败');
  } finally {
    generating.value = false;
  }
};

// 监听 videoId 变化
watch(() => props.videoId, () => {
  loadSummary();
  loadKnowledge();
}, { immediate: true });

onMounted(() => {
  loadSummary();
  loadKnowledge();
});
</script>

<style lang="scss" scoped>
.video-summary-container {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-card);
}

.summary-header {
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--divider-color);
}

.summary-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.summary-loading {
  padding: var(--space-4) 0;
}

.summary-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-4);
  color: var(--text-tertiary);
  
  .el-icon {
    font-size: 48px;
    margin-bottom: var(--space-2);
    opacity: 0.5;
  }
  
  p {
    margin: 0 0 var(--space-3);
    font-size: var(--font-size-sm);
  }
}

.summary-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.summary-section {
  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-2);
  }
  
  .section-title {
    font-size: var(--font-size-base);
    font-weight: var(--font-weight-semibold);
    color: var(--text-primary);
  }
  
  .section-content {
    font-size: var(--font-size-base);
    color: var(--text-secondary);
    line-height: 1.6;
    max-height: 120px;
    overflow: hidden;
    transition: max-height var(--transition-slow);
    
    &.expanded {
      max-height: 1000px;
    }
  }
}

.knowledge-section {
  .knowledge-content {
    display: flex;
    flex-direction: column;
    gap: var(--space-4);
  }
  
  .knowledge-group {
    .knowledge-group-title {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      font-size: var(--font-size-base);
      font-weight: var(--font-weight-semibold);
      color: var(--text-primary);
      margin-bottom: var(--space-2);
      
      .el-icon {
        color: var(--bili-pink);
      }
    }
    
    .knowledge-list {
      margin: 0;
      padding-left: var(--space-5);
      color: var(--text-secondary);
      line-height: 1.8;
      
      li {
        margin-bottom: var(--space-2);
        
        &:last-child {
          margin-bottom: 0;
        }
      }
    }
    
    .steps-list {
      counter-reset: step-counter;
      
      li {
        counter-increment: step-counter;
        list-style: none;
        position: relative;
        padding-left: var(--space-6);
        
        &::before {
          content: counter(step-counter) '.';
          position: absolute;
          left: 0;
          font-weight: var(--font-weight-semibold);
          color: var(--bili-pink);
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .summary-section {
    .section-content {
      font-size: var(--font-size-sm);
    }
  }
}
</style>

