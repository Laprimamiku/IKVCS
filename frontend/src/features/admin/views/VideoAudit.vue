<template>
  <div class="audit-page">
    <div class="page-header">
      <h2>待审核视频</h2>
      <el-button class="refresh-btn" @click="loadData">
        <i class="iconfont icon-refresh"></i> 刷新
      </el-button>
    </div>

    <div class="video-grid" v-if="videos.length > 0">
      <div class="audit-card" v-for="video in videos" :key="video.id">
        <div class="cover-wrapper" @click="openPreview(video)">
          <img :src="video.cover_url" alt="cover" class="cover" />
          <div class="duration">{{ formatDuration(video.duration) }}</div>
          <div class="play-mask"><i class="iconfont icon-play"></i></div>
        </div>
        <div class="info">
          <h3 class="title" :title="video.title">{{ video.title }}</h3>
          <div class="meta">
            <span class="uploader">UP: {{ video.uploader.nickname }}</span>
            <span class="time">{{ formatDate(video.created_at) }}</span>
          </div>
          <div class="actions">
            <el-button type="danger" size="small" @click="handleAudit(video.id, 'reject')">
              拒绝
            </el-button>
            <el-button
              type="success" 
              size="small"
              @click="handleAudit(video.id, 'approve')"
            >
              通过
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { adminApi, type AuditVideoItem } from "../api/admin.api";
import { formatDuration } from "@/shared/utils/formatters";

const videos = ref<AuditVideoItem[]>([]);
const previewVideo = ref<AuditVideoItem | null>(null);

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString();
};

const loadData = async () => {
  try {
    const res = await adminApi.getPendingVideos();
    // @ts-ignore
    videos.value = res.items;
  } catch (e) {
    console.error(e);
  }
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

onMounted(loadData);
</script>

<style scoped lang="scss">
.audit-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

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
}
</style>
