<template>
  <el-popover
    v-if="result"
    placement="top"
    :width="240"
    trigger="hover"
    popper-class="ai-tag-popper"
  >
    <template #reference>
      <div class="inference-engine-tag" :class="result.source">
        <el-icon v-if="result.source === 'local'"><Lightning /></el-icon>
        <el-icon v-else><Cloudy /></el-icon>
        <span class="source-text">{{ result.source === 'local' ? 'Local' : 'Cloud' }}</span>
      </div>
    </template>
    
    <div class="ai-popover-content">
      <div class="popover-header">
        <span class="source-badge" :class="result.source">
          {{ result.source === 'local' ? 'Local Model' : 'Cloud API' }}
        </span>
        <span class="score" :class="{ 'high': result.score >= 80, 'low': result.score < 60 }">
          {{ result.score }}分
        </span>
      </div>
      
      <div class="confidence-section">
        <div class="label-row">
          <span>置信度</span>
          <span class="value">{{ Math.round(result.confidence * 100) }}%</span>
        </div>
        <el-progress 
          :percentage="Math.round(result.confidence * 100)" 
          :status="getConfidenceStatus(result.confidence)"
          :stroke-width="6"
          :show-text="false"
        />
      </div>
      
      <div class="info-item" v-if="result.category">
        <span class="label">分类:</span>
        <span class="value">{{ result.category }}</span>
      </div>
      
      <div class="reason-box" v-if="result.reason">
        <p class="reason-text">{{ result.reason }}</p>
      </div>
    </div>
  </el-popover>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Lightning, Cloudy } from '@element-plus/icons-vue';
import type { AiAnalysisResult } from '@/shared/types/entity';

const props = defineProps<{
  result?: AiAnalysisResult;
}>();

const getConfidenceStatus = (confidence: number) => {
  if (confidence >= 0.8) return 'success';
  if (confidence >= 0.5) return 'warning';
  return 'exception';
};
</script>

<style scoped lang="scss">
.inference-engine-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: help;
  transition: all 0.2s;
  
  &.local {
    background: #f6ffed;
    color: #52c41a;
    border: 1px solid #b7eb8f;
    
    &:hover {
      background: #d9f7be;
    }
  }
  
  &.cloud {
    background: #e6f7ff;
    color: #1890ff;
    border: 1px solid #91d5ff;
    
    &:hover {
      background: #bae7ff;
    }
  }

  .el-icon {
    font-size: 14px;
  }
}

.ai-popover-content {
  .popover-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #ebeef5;
    
    .source-badge {
      font-size: 12px;
      padding: 2px 6px;
      border-radius: 4px;
      
      &.local {
        background: #f6ffed;
        color: #52c41a;
      }
      
      &.cloud {
        background: #e6f7ff;
        color: #1890ff;
      }
    }
    
    .score {
      font-weight: bold;
      font-size: 16px;
      color: #606266;
      
      &.high { color: #67c23a; }
      &.low { color: #f56c6c; }
    }
  }
  
  .confidence-section {
    margin-bottom: 12px;
    
    .label-row {
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
      font-size: 12px;
      color: #606266;
    }
  }
  
  .info-item {
    display: flex;
    gap: 8px;
    font-size: 12px;
    margin-bottom: 8px;
    
    .label {
      color: #909399;
    }
    
    .value {
      color: #303133;
      font-weight: 500;
    }
  }
  
  .reason-box {
    background: #f4f4f5;
    padding: 8px;
    border-radius: 4px;
    
    .reason-text {
      margin: 0;
      font-size: 12px;
      color: #606266;
      line-height: 1.4;
    }
  }
}
</style>