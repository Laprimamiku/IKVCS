<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>视频审核管理</h2>
      <div class="header-actions">
        <div class="status-filter">
          <el-button
            v-for="status in statusOptions"
            :key="status.value"
            :type="currentStatus === status.value ? 'primary' : 'default'"
            size="small"
            @click="switchStatus(status.value)"
          >
            {{ status.label }}
          </el-button>
        </div>
        <el-button class="refresh-btn" @click="loadData">
          <i class="iconfont icon-refresh"></i> 刷新
        </el-button>
      </div>
    </div>

    <div class="video-grid" v-if="videos.length > 0">
      <div class="audit-card" v-for="video in videos" :key="video.id">
        <div class="cover-wrapper" @click="handleManualReview(video.id)">
          <img :src="video.cover_url" alt="cover" class="cover" />
          <div class="duration">{{ formatDuration(video.duration) }}</div>
          <div v-if="video.status !== undefined && video.status !== 2" class="status-badge" :class="getStatusClass(video.status)">
            {{ getStatusText(video.status) }}
          </div>
          <div class="play-mask"><i class="iconfont icon-play"></i></div>
        </div>
        <div class="info">
          <h3 class="title" :title="video.title">{{ video.title }}</h3>
          <div class="meta">
            <span class="uploader">UP: {{ video.uploader.nickname }}</span>
            <span class="time">{{ formatDate(video.created_at) }}</span>
          </div>
          
          <!-- AI 审核结果展示 -->
          <div v-if="video.review_score !== null && video.review_score !== undefined" class="ai-review-info">
            <div class="review-score">
              <span class="label">AI评分:</span>
              <el-tag 
                :type="getScoreTagType(video.review_score)" 
                size="small"
              >
                {{ video.review_score }}分
              </el-tag>
            </div>
            <div v-if="video.review_report" class="review-details">
              <el-button 
                type="text" 
                size="small" 
                @click="showReviewDetails(video)"
              >
                查看详情
              </el-button>
            </div>
          </div>
          
          <div class="actions">
            <el-button type="primary" size="small" @click="handleView(video.id)">
              人工审核
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="handleReviewFrames(video.id)"
              :loading="reviewingFrames === video.id"
            >
              <el-icon><Refresh /></el-icon>
              抽帧审核
            </el-button>
            <el-button
              type="info"
              size="small"
              @click="handleReviewSubtitle(video.id)"
              :loading="reviewingSubtitle === video.id"
              :disabled="!video.subtitle_url"
            >
              <el-icon><Refresh /></el-icon>
              字幕审核
            </el-button>
            <el-button
              v-if="video.status === 1"
              type="success" 
              size="small"
              @click="handleAudit(video.id, 'approve')"
            >
              通过
            </el-button>
            <el-button
              v-if="video.status === 1"
              type="danger" 
              size="small"
              @click="handleAudit(video.id, 'reject')"
            >
              拒绝
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <div class="empty-state" v-else>
      <div class="empty-icon">📭</div>
      <p>暂时没有待审核的视频，休息一下吧~</p>
    </div>

    <div
      class="preview-modal"
      v-if="previewVideo"
      @click.self="previewVideo = null"
    >
      <div class="modal-content">
        <video
          controls
          :src="previewVideo.video_url"
          class="preview-player"
        ></video>
        <div class="modal-info">
          <h4>{{ previewVideo.title }}</h4>
          <p>{{ previewVideo.description }}</p>
        </div>
        <el-button class="close-btn" @click="previewVideo = null" circle>×</el-button>
      </div>
    </div>

    <!-- AI 审核详情对话框 -->
    <el-dialog
      v-model="reviewDetailsVisible"
      title="AI 审核详情"
      width="600px"
    >
      <div v-if="currentReviewVideo" class="review-details-content">
        <div class="review-section">
          <h4>综合评分</h4>
          <el-tag 
            :type="getScoreTagType(currentReviewVideo.review_score || 0)" 
            size="large"
            style="font-size: 18px; padding: 8px 16px;"
          >
            {{ currentReviewVideo.review_score || 'N/A' }}分
          </el-tag>
        </div>
        
        <div v-if="currentReviewVideo.review_report" class="review-section">
          <h4>审核报告</h4>
          <el-collapse>
            <el-collapse-item v-if="currentReviewVideo.review_report.frame_review" title="帧审核结果（Moondream分析）">
              <div class="review-item">
                <p><strong>审核结论:</strong> {{ currentReviewVideo.review_report.conclusion || '暂无结论' }}</p>
                <p><strong>审核帧数:</strong> {{ currentReviewVideo.review_report.frame_review.total_frames || 0 }} 帧</p>
                <p><strong>平均评分:</strong> {{ currentReviewVideo.review_report.frame_review.avg_score || 'N/A' }} 分</p>
                <p><strong>最低评分:</strong> {{ currentReviewVideo.review_report.frame_review.min_score || 'N/A' }} 分</p>
                <p v-if="currentReviewVideo.review_report.frame_review.violation_count > 0">
                  <strong>违规帧:</strong> 
                  <el-tag type="danger" size="small">
                    {{ currentReviewVideo.review_report.frame_review.violation_count }} 帧（{{ currentReviewVideo.review_report.frame_review.violation_ratio }}%）
                  </el-tag>
                </p>
                <p v-if="currentReviewVideo.review_report.frame_review.suspicious_count > 0">
                  <strong>疑似帧:</strong> 
                  <el-tag type="warning" size="small">
                    {{ currentReviewVideo.review_report.frame_review.suspicious_count }} 帧（{{ currentReviewVideo.review_report.frame_review.suspicious_ratio }}%）
                  </el-tag>
                </p>
                <p v-if="currentReviewVideo.review_report.frame_review.normal_count > 0">
                  <strong>正常帧:</strong> 
                  <el-tag type="success" size="small">
                    {{ currentReviewVideo.review_report.frame_review.normal_count }} 帧
                  </el-tag>
                </p>
              </div>
            </el-collapse-item>
            <el-collapse-item v-if="currentReviewVideo.review_report.subtitle_review" title="字幕审核结果（qwen2.5:0.5b-instruct分析）">
              <div class="review-item">
                <p><strong>审核结论:</strong> 
                  <el-tag 
                    :type="currentReviewVideo.review_report.subtitle_review.is_violation ? 'danger' : currentReviewVideo.review_report.subtitle_review.is_suspicious ? 'warning' : 'success'"
                    size="small"
                  >
                    {{ currentReviewVideo.review_report.subtitle_review.is_violation ? '❌ 违规' : currentReviewVideo.review_report.subtitle_review.is_suspicious ? '⚠️ 疑似' : '✅ 正常' }}
                  </el-tag>
                </p>
                <p><strong>评分:</strong> {{ currentReviewVideo.review_report.subtitle_review.score || 'N/A' }} 分</p>
                <p><strong>违规类型:</strong> {{ currentReviewVideo.review_report.subtitle_review.violation_type || 'none' }}</p>
                <p><strong>详细描述:</strong> {{ currentReviewVideo.review_report.subtitle_review.description || '无描述' }}</p>
              </div>
            </el-collapse-item>
            <el-collapse-item v-else-if="currentReviewVideo.subtitle_url" title="字幕审核结果（qwen2.5:0.5b-instruct分析）">
              <div class="review-item">
                <el-alert
                  title="字幕审核未完成"
                  description="字幕文件存在，但审核未完成或审核失败"
                  type="warning"
                  :closable="false"
                />
              </div>
            </el-collapse-item>
            <el-collapse-item title="最终结果">
              <div class="review-item">
                <p><strong>最终评分:</strong> {{ currentReviewVideo.review_report.final_score || 'N/A' }}</p>
                <p><strong>最终状态:</strong> {{ getStatusText(currentReviewVideo.review_report.final_status || currentReviewVideo.status || 0) }}</p>
                <p v-if="currentReviewVideo.review_report.timestamp">
                  <strong>审核时间:</strong> {{ formatDate(currentReviewVideo.review_report.timestamp) }}
                </p>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        
        <div v-if="currentReviewVideo.review_report?.error" class="review-section">
          <el-alert
            :title="currentReviewVideo.review_report.message || '审核过程中出现错误'"
            type="warning"
            :description="currentReviewVideo.review_report.error"
            show-icon
            :closable="false"
          />
        </div>
      </div>
      <template #footer>
        <el-button @click="reviewDetailsVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 人工审核对话框 -->
    <el-dialog
      v-model="manualReviewVisible"
      title="人工审核"
      width="90%"
      :close-on-click-modal="false"
    >
      <div v-if="loadingManualReview" class="loading-container">
        <el-skeleton :rows="5" animated />
      </div>
      
      <div v-else class="manual-review-content">
        <el-tabs>
          <!-- 原始视频 -->
          <el-tab-pane label="原始视频" name="video">
            <div class="video-container">
              <video
                v-if="originalVideoUrl"
                ref="originalVideoPlayer"
                :src="originalVideoUrl"
                controls
                style="width: 100%; max-height: 600px;"
              >
                您的浏览器不支持视频播放
              </video>
              <el-empty v-else description="原始视频文件不存在" />
            </div>
          </el-tab-pane>
          
          <!-- 字幕内容 -->
          <el-tab-pane label="字幕内容" name="subtitle">
            <div class="subtitle-container">
              <div v-if="subtitleContent" class="subtitle-content">
                <el-alert
                  :title="`字幕文件: ${subtitleContent.file_name} (共 ${subtitleContent.total_entries} 条)`"
                  type="info"
                  :closable="false"
                  style="margin-bottom: 20px;"
                />
                
                <!-- 解析后的字幕列表 -->
                <el-collapse>
                  <el-collapse-item title="解析后的字幕列表" name="parsed">
                    <div class="subtitle-list">
                      <div
                        v-for="(sub, index) in subtitleContent.parsed_subtitles"
                        :key="index"
                        class="subtitle-item"
                      >
                        <div class="subtitle-time">
                          {{ formatSubtitleTime(sub.start_time) }} → {{ formatSubtitleTime(sub.end_time) }}
                        </div>
                        <div class="subtitle-text">{{ sub.text }}</div>
                      </div>
                    </div>
                  </el-collapse-item>
                  
                  <el-collapse-item title="原始文件内容" name="raw">
                    <el-input
                      type="textarea"
                      :value="subtitleContent.raw_content"
                      :rows="20"
                      readonly
                      style="font-family: monospace;"
                    />
                  </el-collapse-item>
                </el-collapse>
              </div>
              <el-empty v-else description="该视频没有字幕文件" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
      
      <template #footer>
        <el-button @click="manualReviewVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, View } from "@element-plus/icons-vue";
import { adminApi, type AuditVideoItem } from "../api/admin.api";
import { formatDuration } from "@/shared/utils/formatters";

const videos = ref<AuditVideoItem[]>([]);
const previewVideo = ref<AuditVideoItem | null>(null);
const currentStatus = ref<number | null>(1); // 默认显示待审核视频
const reReviewing = ref<number | null>(null); // 正在重新审核的视频ID（已废弃，保留兼容）
const reviewDetailsVisible = ref(false); // AI审核详情对话框显示状态
const currentReviewVideo = ref<AuditVideoItem | null>(null); // 当前查看审核详情的视频
const reviewingFrames = ref<number | null>(null); // 正在审核帧的视频ID
const reviewingSubtitle = ref<number | null>(null); // 正在审核字幕的视频ID
const manualReviewVisible = ref(false); // 人工审核对话框显示状态
const currentManualReviewVideo = ref<AuditVideoItem | null>(null); // 当前人工审核的视频
const originalVideoUrl = ref<string>(""); // 原始视频 URL
const originalVideoInfo = ref<any>(null); // 原始视频信息
const subtitleContent = ref<any>(null); // 字幕内容
const loadingManualReview = ref(false); // 加载人工审核数据中

const statusOptions = [
  { label: '全部', value: null },
  { label: '转码中', value: 0 },
  { label: '审核中', value: 1 },
  { label: '已发布', value: 2 },
  { label: '已拒绝', value: 3 },
];

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString();
};

const formatSubtitleTime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  const ms = Math.floor((seconds % 1) * 1000);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
};

const loadData = async () => {
  try {
    // 使用 manage_videos 接口，支持状态筛选
    const res = await adminApi.manageVideos(1, 20, currentStatus.value);
    // @ts-ignore
    videos.value = res.items || res.data?.items || [];
  } catch (e) {
    console.error(e);
  }
};

const switchStatus = (status: number | null) => {
  currentStatus.value = status;
  loadData();
};

const handleAudit = async (id: number, action: "approve" | "reject") => {
  if (!confirm(`确定要${action === "approve" ? "通过" : "拒绝"}该视频吗？`))
    return;
  try {
    if (action === "approve") {
      await adminApi.approveVideo(id);
    } else {
      await adminApi.rejectVideo(id);
    }
    // 移除已处理项
    videos.value = videos.value.filter((v) => v.id !== id);
    if (previewVideo.value?.id === id) previewVideo.value = null;
  } catch (e) {
    alert("操作失败");
  }
};

const openPreview = (video: AuditVideoItem) => {
  previewVideo.value = video;
};

const handleView = (videoId: number) => {
  // 打开人工审核对话框，查看原始视频
  handleManualReview(videoId);
};

const getStatusClass = (status: number): string => {
  switch (status) {
    case 0: return 'status-transcoding';  // 转码中
    case 1: return 'status-reviewing';    // 审核中
    case 2: return 'status-published';    // 已发布
    case 3: return 'status-rejected';     // 拒绝
    case 4: return 'status-deleted';      // 软删除
    default: return '';
  }
};

const getStatusText = (status: number): string => {
  switch (status) {
    case 0: return '转码中';
    case 1: return '审核中';
    case 2: return '已发布';
    case 3: return '已拒绝';
    case 4: return '已删除';
    default: return '未知';
  }
};

const handleReviewFrames = async (videoId: number) => {
  reviewingFrames.value = videoId;
  try {
    await adminApi.reviewFramesOnly(videoId);
    ElMessage.success("抽帧审核任务已启动，请稍后查看结果");
    // 延迟刷新数据，等待审核完成
    setTimeout(() => {
      loadData();
    }, 3000);
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || "抽帧审核启动失败");
  } finally {
    reviewingFrames.value = null;
  }
};

const handleReviewSubtitle = async (videoId: number) => {
  reviewingSubtitle.value = videoId;
  try {
    await adminApi.reviewSubtitleOnly(videoId);
    ElMessage.success("字幕审核任务已启动，请稍后查看结果");
    // 延迟刷新数据，等待审核完成
    setTimeout(() => {
      loadData();
    }, 3000);
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || "字幕审核启动失败");
  } finally {
    reviewingSubtitle.value = null;
  }
};

const handleManualReview = async (videoId: number) => {
  const video = videos.value.find(v => v.id === videoId);
  if (!video) return;
  
  currentManualReviewVideo.value = video;
  manualReviewVisible.value = true;
  originalVideoUrl.value = "";
  subtitleContent.value = null;
  loadingManualReview.value = true;
  
  try {
    // 获取原始视频 URL
    const videoRes = await adminApi.getOriginalVideoUrl(videoId);
    // API 返回格式可能是 {success: true, data: {...}}，需要提取 data
    const videoData = (videoRes as any).data || videoRes;
    originalVideoUrl.value = videoData.file_url || "";
    originalVideoInfo.value = videoData; // 保存视频信息
    console.log("原始视频信息:", videoData);
    
    // 获取字幕内容（根据视频ID查找，不依赖 subtitle_url）
    try {
      const subtitleRes = await adminApi.getSubtitleContent(videoId);
      // API 返回格式可能是 {success: true, data: {...}}，需要提取 data
      const subtitleData = (subtitleRes as any).data || subtitleRes;
      subtitleContent.value = subtitleData;
      console.log("字幕内容:", subtitleData);
    } catch (e: any) {
      console.warn("获取字幕内容失败:", e);
      // 字幕获取失败不影响视频查看
      subtitleContent.value = null;
    }
  } catch (e: any) {
    console.error("获取审核数据失败:", e);
    ElMessage.error(e.response?.data?.message || "获取审核数据失败");
    manualReviewVisible.value = false;
  } finally {
    loadingManualReview.value = false;
  }
};

const handleReReview = async (videoId: number) => {
  try {
    await ElMessageBox.confirm(
      "确定要重新触发AI初审吗？这将重新分析视频的帧和字幕内容，并更新审核结果。",
      "重新触发AI初审",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "info",
      }
    );
    
    reReviewing.value = videoId;
    const res = await adminApi.reReviewVideo(videoId);
    
    ElMessage.success("AI初审任务已启动，请稍后查看审核结果");
    
    // 3秒后刷新数据
    setTimeout(() => {
      loadData();
    }, 3000);
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("重新触发AI初审失败:", error);
      ElMessage.error("重新触发AI初审失败");
    }
  } finally {
    reReviewing.value = null;
  }
};

const getScoreTagType = (score: number): string => {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'danger';
};

const showReviewDetails = (video: AuditVideoItem) => {
  currentReviewVideo.value = video;
  reviewDetailsVisible.value = true;
};

onMounted(loadData);
</script>

<style scoped lang="scss">
.audit-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-filter {
      display: flex;
      gap: 8px;
    }

    .refresh-btn {
      padding: 8px 16px;
      background: #fff;
      border: 1px solid #dcdfe6;
      border-radius: 4px;
      cursor: pointer;
      &:hover {
        color: var(--primary-color);
        border-color: var(--primary-color);
      }
    }
  }

  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
  }

  .audit-card {
    background: #fff;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .cover-wrapper {
      position: relative;
      height: 160px;
      cursor: pointer;

      .cover {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .duration {
        position: absolute;
        bottom: 8px;
        right: 8px;
        background: rgba(0, 0, 0, 0.6);
        color: #fff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 12px;
      }
      .play-mask {
        position: absolute;
        inset: 0;
        background: rgba(0, 0, 0, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        opacity: 0;
        transition: opacity 0.2s;
        .iconfont {
          font-size: 40px;
          color: #fff;
        }
      }
      &:hover .play-mask {
        opacity: 1;
      }
    }

    .info {
      padding: 12px;
      .title {
        font-size: 14px;
        margin-bottom: 8px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .meta {
        font-size: 12px;
        color: #999;
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
      }

      .status-badge {
        position: absolute;
        top: 8px;
        left: 8px;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        color: #fff;
        z-index: 2;
        
        &.status-transcoding {
          background: rgba(255, 193, 7, 0.9);
        }
        
        &.status-reviewing {
          background: rgba(33, 150, 243, 0.9);
        }
        
        &.status-rejected {
          background: rgba(244, 67, 54, 0.9);
        }
        
        &.status-published {
          background: rgba(76, 175, 80, 0.9);
        }
        
        &.status-deleted {
          background: rgba(158, 158, 158, 0.9);
        }
      }
      
      .ai-review-info {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 0;
        margin-bottom: 8px;
        border-top: 1px solid #f0f0f0;
        border-bottom: 1px solid #f0f0f0;
        
        .review-score {
          display: flex;
          align-items: center;
          gap: 8px;
          
          .label {
            font-size: 12px;
            color: #666;
          }
        }
        
        .review-details {
          .el-button {
            padding: 0;
            font-size: 12px;
          }
        }
      }
      
      .actions {
        display: flex;
        gap: 10px;
        .btn {
          flex: 1;
          padding: 6px 0;
          border-radius: 4px;
          border: none;
          cursor: pointer;
          font-size: 13px;
          &.reject {
            background: #f5f5f5;
            color: #666;
            &:hover {
              background: #e7e7e7;
            }
          }
          &.approve {
            background: var(--primary-color);
            color: #fff;
            &:hover {
              opacity: 0.9;
            }
          }
        }
      }
    }
  }

  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: #999;
    
    .empty-icon {
      font-size: 64px;
      margin-bottom: 16px;
      opacity: 0.5;
    }
    
    p {
      font-size: 14px;
      color: #999;
    }
  }

  .preview-modal {
    position: fixed;
    inset: 0;
    z-index: 100;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;

    .modal-content {
      background: #fff;
      width: 600px;
      border-radius: 8px;
      padding: 20px;
      position: relative;

      .preview-player {
        width: 100%;
        max-height: 400px;
        background: #000;
        margin-bottom: 16px;
      }
      .close-btn {
        position: absolute;
        top: -40px;
        right: 0;
        font-size: 30px;
        color: #fff;
        background: none;
        border: none;
        cursor: pointer;
      }
    }
  }
  
  .review-details-content {
    .review-section {
      margin-bottom: 20px;
      
      h4 {
        margin-bottom: 12px;
        font-size: 14px;
        font-weight: 600;
        color: #333;
      }
      
      .review-item {
        p {
          margin: 8px 0;
          font-size: 13px;
          line-height: 1.6;
          
          strong {
            color: #666;
            margin-right: 8px;
          }
        }
      }
    }
  }
}
</style>
