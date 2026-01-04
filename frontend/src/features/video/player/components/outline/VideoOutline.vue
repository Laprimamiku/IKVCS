<template>
  <div class="video-outline-container">
    <div class="outline-header">
      <h3 class="outline-title">
        <el-icon><List /></el-icon>
        视频章节
      </h3>
      <div class="outline-count" v-if="outlineList.length > 0">
        {{ outlineList.length }} 个章节
      </div>
    </div>

    <div v-if="loading" class="outline-loading">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="outlineList.length === 0" class="outline-empty">
      <el-icon><Document /></el-icon>
      <p>暂无章节信息</p>
    </div>

    <div v-else class="outline-list mindmap">
      <div
        v-for="(item, index) in outlineList"
        :key="index"
        class="outline-item mindmap-item"
        :class="{ active: isActive(item.start_time) }"
        @click="handleJump(item.start_time)"
      >
        <div class="mindmap-node">
          <div class="mindmap-node-content">
            <div class="mindmap-node-header">
              <span class="mindmap-node-index">{{ index + 1 }}</span>
              <span class="mindmap-node-title">{{ item.title }}</span>
              <span class="mindmap-node-time">{{ formatTime(item.start_time) }}</span>
            </div>
            <div v-if="item.description" class="mindmap-node-desc">
              {{ item.description }}
            </div>
            <!-- 关键知识点/内容点 -->
            <div v-if="item.key_points && item.key_points.length > 0" class="mindmap-node-points">
              <div 
                v-for="(point, idx) in item.key_points"
                :key="idx"
                class="mindmap-node-point"
              >
                <el-icon class="point-icon"><Star /></el-icon>
                <span>{{ point }}</span>
              </div>
            </div>
          </div>
          <!-- 连接线（思维导图样式） -->
          <div v-if="index < outlineList.length - 1" class="mindmap-connector"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { List, Document } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import type { VideoOutlineEntry } from '@/shared/types/entity';
import { getVideoOutline } from '@/features/video/shared/api/video.api';

interface Props {
  videoId: number;
  currentTime?: number; // 当前播放时间（秒）
}

interface Emits {
  (e: 'jump', time: number): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const loading = ref(false);
const outlineData = ref<VideoOutlineEntry[]>([]);

// 解析大纲数据（可能是JSON字符串或对象数组）
const outlineList = computed(() => {
  if (!outlineData.value || outlineData.value.length === 0) {
    return [];
  }
  return outlineData.value;
});

// 判断当前播放位置是否在某个章节
const isActive = (startTime: number) => {
  if (props.currentTime === undefined) return false;
  
  const currentIndex = outlineList.value.findIndex(
    (item, index) => {
      const nextItem = outlineList.value[index + 1];
      const endTime = nextItem ? nextItem.start_time : Infinity;
      return props.currentTime! >= startTime && props.currentTime! < endTime;
    }
  );
  
  const itemIndex = outlineList.value.findIndex(item => item.start_time === startTime);
  return currentIndex === itemIndex;
};

// 格式化时间
const formatTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  }
  return `${minutes}:${String(secs).padStart(2, '0')}`;
};

// 跳转到指定时间
const handleJump = (time: number) => {
  emit('jump', time);
};

// 加载大纲数据
const loadOutline = async () => {
  if (!props.videoId) return;
  
  loading.value = true;
  try {
    const response = await getVideoOutline(props.videoId);
    if (response.success && response.data) {
      // 处理大纲数据（可能是JSON字符串）
      let outline = response.data.outline;
      if (typeof outline === 'string') {
        try {
          outline = JSON.parse(outline);
        } catch (e) {
          console.error('解析大纲JSON失败:', e);
          outline = [];
        }
      }
      
      // 确保是数组并按时间排序
      if (Array.isArray(outline)) {
        // 确保每个条目的 key_points 是数组格式
        outline = outline.map((item: any) => {
          if (item.key_points) {
            // 如果 key_points 是字符串，尝试解析或分割
            if (typeof item.key_points === 'string') {
              try {
                item.key_points = JSON.parse(item.key_points);
              } catch {
                // 如果解析失败，按逗号分割
                item.key_points = item.key_points.split(',').map((p: string) => p.trim()).filter((p: string) => p);
              }
            }
            // 确保是数组
            if (!Array.isArray(item.key_points)) {
              item.key_points = [];
            }
          } else {
            item.key_points = [];
          }
          return item;
        });
        
        outlineData.value = outline.sort((a, b) => a.start_time - b.start_time);
      } else {
        outlineData.value = [];
      }
    } else {
      outlineData.value = [];
    }
  } catch (error) {
    console.error('加载视频大纲失败:', error);
    ElMessage.error('加载视频大纲失败');
    outlineData.value = [];
  } finally {
    loading.value = false;
  }
};

// 监听 videoId 变化
watch(() => props.videoId, () => {
  loadOutline();
}, { immediate: true });

onMounted(() => {
  loadOutline();
});
</script>

<style lang="scss" scoped>
.video-outline-container {
  background: var(--bg-white);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  box-shadow: var(--shadow-card);
}

.outline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--divider-color);
}

.outline-title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
  margin: 0;
}

.outline-count {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.outline-loading {
  padding: var(--space-4) 0;
}

.outline-empty {
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
    margin: 0;
    font-size: var(--font-size-sm);
  }
}

.outline-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  
  &.mindmap {
    position: relative;
    padding-left: 20px;
    
    &::before {
      content: '';
      position: absolute;
      left: 10px;
      top: 0;
      bottom: 0;
      width: 2px;
      background: linear-gradient(to bottom, var(--bili-pink), rgba(251, 114, 153, 0.3));
      border-radius: 2px;
    }
  }
}

.outline-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: var(--transition-fast);
  border: 1px solid transparent;
  
  &:hover {
    background: var(--bg-hover);
    border-color: var(--divider-color);
  }
  
  &.active {
    background: var(--bili-pink-light);
    border-color: var(--bili-pink);
    
    .outline-item-title,
    .mindmap-node-title {
      color: var(--bili-pink);
      font-weight: var(--font-weight-semibold);
    }
  }
  
  &.mindmap-item {
    position: relative;
    padding-left: 0;
    
    .mindmap-node {
      position: relative;
      width: 100%;
      
      .mindmap-node-content {
        background: var(--bg-white);
        border: 1px solid var(--divider-color);
        border-radius: var(--radius-md);
        padding: var(--space-3);
        transition: var(--transition-fast);
        
        &:hover {
          border-color: var(--bili-pink);
          box-shadow: 0 2px 8px rgba(251, 114, 153, 0.1);
        }
      }
      
      .mindmap-connector {
        position: absolute;
        left: -20px;
        top: 50%;
        width: 20px;
        height: 2px;
        background: var(--bili-pink);
        transform: translateY(-50%);
        z-index: 1;
        
        &::after {
          content: '';
          position: absolute;
          right: -4px;
          top: 50%;
          transform: translateY(-50%);
          width: 0;
          height: 0;
          border-left: 6px solid var(--bili-pink);
          border-top: 4px solid transparent;
          border-bottom: 4px solid transparent;
        }
      }
    }
    
    &.active .mindmap-node-content {
      background: var(--bili-pink-light);
      border-color: var(--bili-pink);
    }
  }
}

.outline-item-content {
  flex: 1;
  min-width: 0;
}

.outline-item-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
}

.outline-item-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: var(--radius-circle);
  background: var(--bg-gray-1);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  flex-shrink: 0;
}

.outline-item.active .outline-item-index {
  background: var(--bili-pink);
  color: var(--text-white);
}

.outline-item-title {
  flex: 1;
  font-size: var(--font-size-base);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.outline-item-time {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.outline-item-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-top: var(--space-1);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.outline-item-thumbnail {
  width: 80px;
  height: 45px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  flex-shrink: 0;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.mindmap-node-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.mindmap-node-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-circle);
  background: var(--bg-gray-1);
  color: var(--text-secondary);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
  flex-shrink: 0;
}

.mindmap-item.active .mindmap-node-index {
  background: var(--bili-pink);
  color: var(--text-white);
}

.mindmap-node-title {
  flex: 1;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mindmap-node-time {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.mindmap-node-desc {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.5;
  margin-top: var(--space-1);
  margin-bottom: var(--space-2);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.mindmap-node-points {
  margin-top: var(--space-2);
  padding-top: var(--space-2);
  border-top: 1px solid var(--divider-color);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.mindmap-node-point {
  display: flex;
  align-items: flex-start;
  gap: var(--space-1);
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  line-height: 1.4;
  
  .point-icon {
    color: var(--bili-pink);
    font-size: 14px;
    margin-top: 2px;
    flex-shrink: 0;
  }
  
  span {
    flex: 1;
  }
}

@media (max-width: 768px) {
  .outline-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .outline-item-thumbnail {
    width: 100%;
    height: auto;
    aspect-ratio: 16 / 9;
  }
}
</style>

